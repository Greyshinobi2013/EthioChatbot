import streamlit as st
from pathlib import Path

FACES_DIR = Path("faces")
FACES_DIR.mkdir(exist_ok=True)

st.title("📷 Enroll Face")

if "logs" not in st.session_state:
    st.session_state.logs = []


def add_log(message):
    st.session_state.logs.insert(0, message)


user_name = st.text_input(
    "User Name / ID"
)

uploaded_file = st.file_uploader(
    "Upload Face Image",
    type=["jpg", "jpeg", "png"]
)

if uploaded_file:
    st.image(uploaded_file, width=300)

if st.button("Save Enrollment"):

    if not user_name:
        st.warning("Please enter a user ID.")

    elif uploaded_file is None:
        st.warning("Please upload an image.")

    else:

        destination = (
            FACES_DIR /
            f"{user_name}.jpg"
        )

        with open(destination, "wb") as file:
            file.write(
                uploaded_file.read()
            )

        add_log(
            f"Face enrolled: {user_name}"
        )

        st.success(
            f"{user_name} enrolled successfully."
        )
