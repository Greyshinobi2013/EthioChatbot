import streamlit as st
import os
import json

st.set_page_config(page_title="Offline Chatbot", layout="wide")

# Ensure directories
os.makedirs("faces", exist_ok=True)
os.makedirs("audio", exist_ok=True)
os.makedirs("config", exist_ok=True)

CONFIG_PATH = "config/dialog_config.json"

# Create default config
if not os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "w") as f:
        json.dump({
            "english": {
                "greeting": ["Hello! How can I help you?"]
            }
        }, f, indent=2)

# Session state
if "session" not in st.session_state:
    st.session_state.session = {
        "user": None,
        "scenario": None,
        "vad": False,
        "last_text": ""
    }

if "settings" not in st.session_state:
    st.session_state.settings = {
        "tolerance": 0.5,
        "whisper": "base",
        "vad": 1,
        "interrupt": "Restart Clip"
    }

st.title("🤖 Offline Multimodal Chatbot")

st.sidebar.header("System Status")
st.sidebar.write(st.session_state.session)

st.markdown("Use sidebar to navigate pages.")