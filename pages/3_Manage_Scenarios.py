import streamlit as st
import json
from pathlib import Path

DEFAULT_CONFIG = "config/dialog_config.json"

st.title("🎭 Manage Scenarios")

if "playback_status" not in st.session_state:
    st.session_state.playback_status = "Stopped"

if "logs" not in st.session_state:
    st.session_state.logs = []


def add_log(message):
    st.session_state.logs.insert(0, message)


config_path = st.text_input(
    "Scenario JSON Path",
    DEFAULT_CONFIG
)

if st.button("Reload Configuration"):
    add_log("Scenario configuration reloaded")
    st.success("Configuration reloaded")

# --------------------------------------------------
# Load Config
# --------------------------------------------------
try:

    with open(
        config_path,
        "r",
        encoding="utf-8"
    ) as file:

        scenarios = json.load(file)

    st.subheader(
        "Available Scenarios"
    )

    for language, dialogs in scenarios.items():

        with st.expander(
            f"🌐 {language}"
        ):

            st.json(dialogs)

except Exception as e:
    st.error(
        f"Cannot load configuration:\n{e}"
    )

# --------------------------------------------------
# Playback Controls
# --------------------------------------------------
st.divider()

col1, col2, col3 = st.columns(3)

if col1.button("▶ Play"):

    st.session_state.playback_status = (
        "Playing"
    )

    add_log("Scenario playback started")

if col2.button("⏸ Pause"):

    st.session_state.play