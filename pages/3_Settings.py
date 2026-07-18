"""Settings page for EthioChatbot V2's Streamlit dashboard.

Presentation-layer only: collects setting values and delegates
loading/saving to app.py's AppConfig/load_configuration()/
save_configuration(), per ARCHITECTURE.md's rule that Streamlit pages
must not contain business logic. Does not touch the live running
Application: changes take effect the next time the application starts,
since the running engine's services were already constructed from
whatever configuration was in effect at that time.
"""
from __future__ import annotations

import streamlit as st

from app import AppConfig, ConfigurationError, load_configuration, save_configuration

st.set_page_config(page_title="Settings - EthioChatbot V2", page_icon="⚙️")
st.title("Settings")
st.caption("Changes are saved to config/settings.json and take effect the next time the application starts.")

try:
    config = load_configuration()
except ConfigurationError as exc:
    st.error(f"Could not load configuration: {exc}")
    st.stop()

WHISPER_MODEL_SIZES = ["tiny", "base", "small", "medium", "large"]

st.subheader("Camera Settings")
camera_index = st.number_input("Camera index", min_value=0, value=config.camera_index, step=1)
camera_width = st.number_input("Camera width", min_value=1, value=config.camera_width, step=1)
camera_height = st.number_input("Camera height", min_value=1, value=config.camera_height, step=1)
recognition_interval = st.number_input(
    "Recognition interval (recognize every Nth frame)",
    min_value=1,
    value=config.recognition_interval,
    step=1,
)
face_confidence = st.slider(
    "Face confidence threshold (max embedding distance)",
    min_value=0.0,
    max_value=1.0,
    value=config.face_confidence,
)
face_lost_timeout = st.number_input(
    "Face lost timeout (seconds)", min_value=1, value=config.face_lost_timeout, step=1
)

st.subheader("Whisper Settings")
whisper_model_index = (
    WHISPER_MODEL_SIZES.index(config.whisper_model) if config.whisper_model in WHISPER_MODEL_SIZES else 1
)
whisper_model = st.selectbox("Whisper model", WHISPER_MODEL_SIZES, index=whisper_model_index)

st.subheader("VAD Settings")
vad_aggressiveness = st.slider("VAD aggressiveness", min_value=0, max_value=3, value=config.vad_aggressiveness)

st.subheader("Audio Input Settings")
audio_input_device = st.number_input(
    "Microphone device index (-1 = auto-detect)",
    min_value=-1,
    value=config.audio_input_device if config.audio_input_device is not None else -1,
    step=1,
    help=(
        "sounddevice input device index to prefer, e.g. 3. If unset (-1) "
        "or the device fails validation at startup, utils/audio_service.py "
        "automatically falls back to probing known-working device indices."
    ),
)

st.subheader("Timeout Settings")
conversation_timeout = st.number_input(
    "Conversation timeout (seconds)", min_value=1, value=config.conversation_timeout, step=1
)

if st.button("Save Settings", type="primary"):
    updated_config = AppConfig(
        camera_index=int(camera_index),
        camera_width=int(camera_width),
        camera_height=int(camera_height),
        whisper_model=whisper_model,
        recognition_interval=int(recognition_interval),
        face_confidence=float(face_confidence),
        face_lost_timeout=int(face_lost_timeout),
        vad_aggressiveness=int(vad_aggressiveness),
        conversation_timeout=int(conversation_timeout),
        audio_input_device=int(audio_input_device) if int(audio_input_device) >= 0 else None,
    )
    try:
        save_configuration(updated_config)
        st.success("Settings saved to config/settings.json. Restart the application for changes to take effect.")
    except ConfigurationError as exc:
        st.error(str(exc))
