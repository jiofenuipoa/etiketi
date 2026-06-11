import streamlit as st
import easyocr
import pandas as pd
import numpy as np
from PIL import Image

st.set_page_config(
    page_title="Сканиране на хранителни съставки",
    page_icon="🔍"
)

@st.cache_resource
def create_reader():
    return easyocr.Reader(["bg", "en"])

ocr_reader = create_reader()

INGREDIENTS = {

    # ВРЕДНИ / СПОРНИ

    "хидрогенирано растително масло": {
        "group": "Вредни",
        "info": "Източник на трансмазнини."
    },

    "глюкозо-фруктозен сироп": {
        "group": "Вредни",
        "info": "Свързва се с повишен риск от затлъстяване."
    },

    "аспартам": {
        "group": "Спорни",
        "info": "Изкуствен подсладител (E951)."
    },

    "ацесулфам к": {
        "group": "Спорни",
        "info": "Подсладител E950."
    },

    "натриев нитрит": {
        "group": "Вредни",
        "info": "Консервант E250 в колбаси."
    },

    "натриев нитрат": {
        "group": "Вредни",
        "info": "Консервант E251."
    },

    "мононатриев глутамат": {
        "group": "Спорни",
        "info": "Овкусител E621."
    },

    "палмово масло": {
        "group": "Спорни",
        "info": "Често силно преработено."
    },

    "титанов диоксид": {
        "group": "Вредни",
        "info": "Оцветител E171."
    },

    # ПОЛЕЗНИ

    "овесени ядки": {
        "group": "Полезни",
        "info": "Богати на фибри."
    },

    "ленено семе": {
        "group": "Полезни",
        "info": "Източник на Омега-3."
    },

    "чия": {
        "group": "Полезни",
        "info": "Богата на фибри и минерали."
    },

    "куркума": {
        "group": "Полезни",
        "info": "Съдържа куркумин."
    },

    "канела": {
        "group": "Полезни",
        "info": "Антиоксидантни свойства."
    },

    "зехтин": {
        "group": "Полезни",
        "info": "Полезни мононенаситени мазнини."
    },

    # БЕЗВРЕДНИ

    "пшенично брашно": {
        "group": "Безвредни",
        "info": "Стандартна суровина."
    },

    "сол": {
        "group": "Безвредни",
        "info": "Нормална хранителна съставка."
    },

    "захар": {
        "group": "Безвредни",
        "info": "Да се консумира умерено."
    },

    "вода": {
        "group": "Безвредни",
        "info": "Основна съставка."
    },

    # Е-ТА

    "e100": {
        "group": "Полезни",
        "info": "Куркумин."
    },

    "e101": {
        "group": "Безвредни",
        "info": "Рибофлавин (витамин B2)."
    },

    "e160a": {
        "group": "Безвредни",
        "info": "Бета-каротин."
    },

    "e200": {
        "group": "Безвредни",
        "info": "Сорбинова киселина."
    },

    "e202": {
        "group": "Безвредни",
        "info": "Калиев сорбат."
    },

    "e211": {
        "group": "Спорни",
        "info": "Натриев бензоат."
    },

    "e220": {
        "group": "Спорни",
        "info": "Серен диоксид."
    },

    "e250": {
        "group": "Вредни",
        "info": "Натриев нитрит."
    },

    "e251": {
        "group": "Вредни",
        "info": "Натриев нитрат."
    },

    "e300": {
        "group": "Полезни",
        "info": "Витамин C."
    },

    "e322": {
        "group": "Безвредни",
        "info": "Лецитин."
    },

    "e330": {
        "group": "Безвредни",
        "info": "Лимонена киселина."
    },

    "e407": {
        "group": "Спорни",
        "info": "Карагенан."
    },

    "e412": {
        "group": "Безвредни",
        "info": "Гуарова гума."
    },

    "e415": {
        "group": "Безвредни",
        "info": "Ксантанова гума."
    },

    "e471": {
        "group": "Безвредни",
        "info": "Моно- и диглицериди."
    },

    "e621": {
        "group": "Спорни",
        "info": "Мононатриев глутамат."
    },

    "e950": {
        "group": "Спорни",
        "info": "Ацесулфам K."
    },

    "e951": {
        "group": "Спорни",
        "info": "Аспартам."
    },

    "e955": {
        "group": "Спорни",
        "info": "Сукралоза."
    },

    "e960": {
        "group": "Полезни",
        "info": "Стевия."
    }
}

OCR_ALIASES = {

    # масла
    "хидрогенира": "хидрогенирано растително масло",
    "палмово": "палмово масло",

    # подсладители
    "аспартам": "аспартам",
    "ацесулфам": "ацесулфам к",

    # овкусители
    "глутамат": "мононатриев глутамат",

    # нитрити
    "нитрит": "натриев нитрит",
    "нитрат": "натриев нитрат",

    # полезни
    "овесени": "овесени ядки",
    "ленено": "ленено семе",
    "чия": "чия",
    "куркума": "куркума",
    "канела": "канела",
    "зехтин": "зехтин",

    # е-та
    "e100": "e100",
    "e101": "e101",
    "e160": "e160a",
    "e200": "e200",
    "e202": "e202",
    "e211": "e211",
    "e220": "e220",
    "e250": "e250",
    "e251": "e251",
    "e300": "e300",
    "e322": "e322",
    "e330": "e330",
    "e407": "e407",
    "e412": "e412",
    "e415": "e415",
    "e471": "e471",
    "e621": "e621",
    "e950": "e950",
    "e951": "e951",
    "e955": "e955",
    "e960": "e960"
}

def extract_text(image_obj):
    image_array = np.array(image_obj)
    result = ocr_reader.readtext(image_array)

    return " ".join(
        item[1].lower()
        for item in result
    )


def detect_ingredients(text):
    matches = []

    for keyword, ingredient in OCR_ALIASES.items():
        if keyword in text:
            data = INGREDIENTS.get(ingredient)

            if data:
                matches.append({
                    "Съставка": ingredient.title(),
                    "Категория": data["group"],
                    "Описание": data["info"]
                })

    return matches


st.title("🔍 Проверка на хранителни съставки")

input_mode = st.selectbox(
    "Избери източник",
    ["Качи изображение", "Използвай камера"]
)

photo = None

if input_mode == "Качи изображение":
    uploaded = st.file_uploader(
        "Избери файл",
        type=["png", "jpg", "jpeg"]
    )

    if uploaded:
        photo = Image.open(uploaded)

else:
    captured = st.camera_input("Направи снимка")

    if captured:
        photo = Image.open(captured)

if photo:

    st.image(photo, use_container_width=True)

    with st.spinner("Разпознаване на текст..."):
        raw_text = extract_text(photo)

    st.subheader("Открит текст")

    with st.expander("Покажи OCR резултат"):
        st.write(raw_text)

    ingredients_found = detect_ingredients(raw_text)

    st.subheader("Резултат")

    if ingredients_found:

        results_df = pd.DataFrame(ingredients_found)

        priority = {
            "Полезни": 1,
            "Безвредни": 2,
            "Вредни": 3
        }

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
                st.success(
                    f"**{row['Съставка']}**\n\n{row['Описание']}"
                )

            elif row["Категория"] == "Безвредни":
                st.info(
                    f"**{row['Съставка']}**\n\n{row['Описание']}"
                )

            else:
                st.warning(
                    f"**{row['Съставка']}**\n\n{row['Описание']}"
                )

    else:
        st.error("Не са открити познати съставки.")
