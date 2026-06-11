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
    "хидрогенирано растително масло": {
        "group": "Вредни",
        "info": "Източник на трансмазнини и повишен риск от сърдечно-съдови заболявания."
    },
    "глюкозо-фруктозен сироп": {
        "group": "Вредни",
        "info": "Свързва се с инсулинова резистентност и натрупване на висцерални мазнини."
    },
    "пшенично брашно": {
        "group": "Безвредни",
        "info": "Стандартна суровина за тестени изделия."
    },
    "канела": {
        "group": "Полезни",
        "info": "Съдържа антиоксиданти и подпомага контрола на кръвната захар."
    }
}

OCR_ALIASES = {
    "хидрогенира": "хидрогенирано растително масло",
    "фруктозен": "глюкозо-фруктозен сироп",
    "пшенично": "пшенично брашно",
    "канела": "канела"
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
