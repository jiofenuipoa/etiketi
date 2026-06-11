import streamlit as st
import easyocr
import pandas as pd
import numpy as np
import json
import re
from PIL import Image

st.set_page_config(
    page_title="Сканиране на хранителни съставки",
    page_icon="🔍"
)

# 1. Оптимизиран Рийдър: gpu=False и лимит на нишките спират безкрайното въртене
@st.cache_resource
def create_reader():
    return easyocr.Reader(["bg", "en"], gpu=False)

ocr_reader = create_reader()

# 2. Вградена база данни (директно от вашия JSON)
INGREDIENTS = {
  "аспартам": {"group": "Спорни", "info": "Изкуствен подсладител. Съответства на E951."},
  "ацесулфам к": {"group": "Спорни", "info": "Изкуствен подсладител. Съответства на E950."},
  "сукралоза": {"group": "Спорни", "info": "Изкуствен подсладител. Съответства на E955."},
  "стевия": {"group": "Полезни", "info": "Естествен подсладител."},
  "глюкозо-фруктозен сироп": {"group": "Вредни", "info": "Свързва се с повишен риск от затлъстяване."},
  "палмово масло": {"group": "Спорни", "info": "Често силно преработено."},
  "хидрогенирано растително масло": {"group": "Вредни", "info": "Източник на трансмазнини."},
  "мононатриев глутамат": {"group": "Спорни", "info": "Подобрител на вкуса. Съответства на E621."},
  "натриев нитрит": {"group": "Вредни", "info": "Консервант в колбаси. Съответства на E250."},
  "натриев нитрат": {"group": "Вредни", "info": "Консервант. Съответства на E251."},
  "e100": {"group": "Полезни", "info": "Куркумин."},
  "e101": {"group": "Безвредни", "info": "Рибофлавин (витамин B2)."},
  "e102": {"group": "Спорни", "info": "Тартразин."},
  "e110": {"group": "Спорни", "info": "Жълт оцветител Sunset Yellow."},
  "e120": {"group": "Безвредни", "info": "Кармин."},
  "e122": {"group": "Спорни", "info": "Азорубин."},
  "e124": {"group": "Спорни", "info": "Понсо 4R."},
  "e129": {"group": "Спорни", "info": "Allura Red."},
  "e133": {"group": "Безвредни", "info": "Brilliant Blue."},
  "e150a": {"group": "Безвредни", "info": "Карамелен оцветител."},
  "e160a": {"group": "Безвредни", "info": "Бета-каротин."},
  "e160c": {"group": "Безвредни", "info": "Паприка екстракт."},
  "e162": {"group": "Безвредни", "info": "Червено цвекло."},
  "e171": {"group": "Вредни", "info": "Титанов диоксид."},
  "e200": {"group": "Безвредни", "info": "Сорбинова киселина."},
  "e202": {"group": "Безвредни", "info": "Калиев сорбат."},
  "e211": {"group": "Спорни", "info": "Натриев бензоат."},
  "e220": {"group": "Спорни", "info": "Серен диоксид."},
  "e250": {"group": "Вредни", "info": "Натриев нитрит."},
  "e251": {"group": "Вредни", "info": "Натриев нитрат."},
  "e262": {"group": "Безвредни", "info": "Натриев ацетат."},
  "e290": {"group": "Безвредни", "info": "Въглероден диоксид."},
  "e300": {"group": "Полезни", "info": "Витамин C."},
  "e301": {"group": "Полезни", "info": "Натриев аскорбат."},
  "e306": {"group": "Полезни", "info": "Токофероли (витамин E)."},
  "e322": {"group": "Безвредни", "info": "Лецитин."},
  "e330": {"group": "Безвредни", "info": "Лимонена киселина."},
  "e407": {"group": "Спорни", "info": "Карагенан."},
  "e410": {"group": "Безвредни", "info": "Гума от рожков."},
  "e412": {"group": "Безвредни", "info": "Гуарова гума."},
  "e415": {"group": "Безвредни", "info": "Ксантанова гума."},
  "e440": {"group": "Безвредни", "info": "Пектин."},
  "e450": {"group": "Спорни", "info": "Фосфати."},
  "e471": {"group": "Безвредни", "info": "Моно- и диглицериди."},
  "e500": {"group": "Безвредни", "info": "Сода бикарбонат."},
  "e551": {"group": "Безвредни", "info": "Силициев диоксид."},
  "e621": {"group": "Спорни", "info": "Мононатриев глутамат."},
  "e950": {"group": "Спорни", "info": "Ацесулфам K."},
  "e951": {"group": "Спорни", "info": "Аспартам."},
  "e955": {"group": "Спорни", "info": "Сукралоза."},
  "e960": {"group": "Полезни", "info": "Стевия."},
  "овесени ядки": {"group": "Полезни", "info": "Богати на фибри."},
  "ленено семе": {"group": "Полезни", "info": "Източник на Омега-3."},
  "чия": {"group": "Полезни", "info": "Богата на фибри и минерали."},
  "куркума": {"group": "Полезни", "info": "Съдържа куркумин."},
  "канела": {"group": "Полезни", "info": "Антиоксидантни свойства."},
  "зехтин": {"group": "Полезни", "info": "Полезни мононенаситени мазнини."}
}

OCR_ALIASES = {
    "хидрогенира": "хидрогенирано растително масло",
    "палмово": "палмово масло",
    "аспартам": "аспартам",
    "ацесулфам": "ацесулфам к",
    "глутамат": "мононатриев глутамат",
    "нитрит": "натриев нитрит",
    "нитрат": "натриев нитрат",
    "овесени": "овесени ядки",
    "ленено": "ленено семе",
    "чия": "чия",
    "куркума": "куркума",
    "канела": "канела",
    "зехтин": "зехтин"
}

def normalize_text(text):
    text = text.lower()
    replacements = {
        "€": "e",
        "[": "e",
        "]": "",
        "(": "",
        ")": "",
        "{": "",
        "}": "",
        "|": "",
        "\n": " "
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

# КЕШИРАНЕ: Ограничаваме процеса до 1 работна нишка (workers=1), за да няма забиване
@st.cache_data
def extract_text(image_array):
    result = ocr_reader.readtext(image_array, paragraph=True, workers=1)
    text = " ".join(item[1] for item in result)
    return normalize_text(text)

def detect_ingredients(text):
    matches = []
    found = set()

    for keyword, ingredient in OCR_ALIASES.items():
        if keyword in text:
            if ingredient in found:
                continue
            data = INGREDIENTS.get(ingredient)
            if data:
                found.add(ingredient)
                matches.append({
                    "Съставка": ingredient.title(),
                    "Категория": data["group"],
                    "Описание": data["info"]
                })

    # Хваща и българско 'е', и латинско 'e'
    e_numbers = re.findall(r"[eе]\s?\d{3,4}[a-z]?", text)

    for e_code in e_numbers:
        e_code = e_code.replace(" ", "").replace("е", "e")

        if e_code in found:
            continue

        if e_code in INGREDIENTS:
            data = INGREDIENTS[e_code]
            found.add(e_code)
            matches.append({
                "Съставка": e_code.upper(),
                "Категория": data["group"],
                "Описание": data["info"]
            })

    return matches

def calculate_score(results):
    score = 100
    for item in results:
        if item["Категория"] == "Вредни":
            score -= 20
        elif item["Категория"] == "Спорни":
            score -= 10
    return max(score, 0)


st.title("🔍 Проверка на хранителни съставки")

input_mode = st.selectbox(
    "Избери източник",
    ["Качи изображение", "Използвай камера"]
)

photo = None

if input_mode == "Качи изображение":
    uploaded = st.file_uploader("Избери файл", type=["png", "jpg", "jpeg"])
    if uploaded:
        photo = Image.open(uploaded)
else:
    captured = st.camera_input("Направи снимка")
    if captured:
        photo = Image.open(captured)

if photo:
    # ОПТИМИЗАЦИЯ НА РАЗМЕРА: Свива снимката, ако е огромна. 
    # Това ускорява EasyOCR десетки пъти на CPU!
    max_width = 1000
    if photo.width > max_width:
        w_percent = (max_width / float(photo.width))
        h_size = int((float(photo.height) * float(w_percent)))
        photo = photo.resize((max_width, h_size), Image.Resampling.LANCZOS)

    st.image(photo, use_container_width=True)

    image_array = np.array(photo)

    with st.spinner("Разпознаване на текст..."):
        raw_text = extract_text(image_array)

    st.subheader("Открит текст")
    with st.expander("Покажи OCR резултат"):
        st.write(raw_text)

    ingredients_found = detect_ingredients(raw_text)

    st.subheader("Резултат")

    if ingredients_found:
        score = calculate_score(ingredients_found)
        st.metric("Оценка на продукта", f"{score}/100")

        if score >= 80:
            st.success("Добър продукт")
        elif score >= 60:
            st.warning("Среден продукт")
        else:
            st.error("Неблагоприятен продукт")

        results_df = pd.DataFrame(ingredients_found)
        priority = {"Полезни": 1, "Безвредни": 2, "Спорни": 3, "Вредни": 4}
        
        results_df = results_df.sort_values(
            by="Категория",
            key=lambda x: x.map(priority)
        )

        st.dataframe(
            results_df[["Съставка", "Категория"]],
            use_container_width=True
        )

        for row in ingredients_found:
            if row["Категория"] == "Полезни":
                st.success(f"**{row['Съставка']}**\n\n{row['Описание']}")
            elif row["Категория"] == "Безвредни":
                st.info(f"**{row['Съставка']}**\n\n{row['Описание']}")
            elif row["Категория"] == "Спорни":
                st.warning(f"**{row['Съставка']}**\n\n{row['Описание']}")
            else:
                st.error(f"**{row['Съставка']}**\n\n{row['Описание']}")
    else:
        st.error("Не са открити познати съставки.")
