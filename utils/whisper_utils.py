import whisper
import streamlit as st

@st.cache_resource
def load_model(size="base"):
    return whisper.load_model(size)

def transcribe_audio(path):
    model = load_model()
    result = model.transcribe(path)
    return result["text"]