import streamlit as st

st.set_page_config(
    page_title="Offline Multimodal Chatbot",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Offline Multimodal Chatbot")

st.markdown("""
Welcome to the Offline Multimodal Chatbot Dashboard.

Use the navigation menu on the left to access:

- Dashboard
- Enroll Face
- Manage Scenarios
- Settings
""")

st.info(
    "All processing runs locally. "
    "Face recognition, VAD, Whisper STT, and playback are server-side."
)