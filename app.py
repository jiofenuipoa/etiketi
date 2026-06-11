import streamlit as st
import easyocr
import pandas as pd
import numpy as np
import json
import re
import io
from PIL import Image

st.set_page_config(
    page_title="Сканиране на хранителни съставки",
    page_icon="🔍"
)

# 1. Кеширане на OCR Рийдъра
@st.cache_resource
def create_reader():
    return easyocr.Reader(["bg", "en"])

ocr_reader = create_reader()

# 2. Зареждане на JSON базата
@st.cache_data
def load_ingredients():
    # За демо цели - ако файлът липсва, правим празен речник, за да не гърми
    try:
        with open("ingredients.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

INGREDIENTS = load_ingredients()

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
    
    # Премахваме само символите, БЕЗ да заменяме кирилско 'е' с латинско 'е' глобално, 
    # за да не счупим търсенето на думи на кирилица.
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

# 3. КЕШИРАНЕ НА OCR ИЗЧИСЛЕНИЯТА
# Подаваме numpy array (който streamlit знае как да кешира), за да не се преизчислява при всяко цъкане
@st.cache_data
def extract_text(image_array):
    result = ocr_reader.readtext(image_array, paragraph=True)
    text = " ".join(item[1] for item in result)
    return normalize_text(text)

def detect_ingredients(text):
    matches = []
    found = set()

    # Търсене по алиаси (на кирилица)
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

    # Търсене на Е-номера (поддържаме проверка и за кирилско 'е', и за латинско 'e')
    # Регулярният израз вече хваща и двете букви
    e_numbers = re.findall(r"[eе]\s?\d{3,4}[a-z]?", text)

    for e_code in e_numbers:
        # Нормализираме намереното към латинско 'e' за проверка в JSON базата
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
    st.image(photo, use_container_width=True)

    # Превръщаме в numpy array тук, за да работи кешът на extract_text правилно
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
