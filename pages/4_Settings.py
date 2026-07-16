"""Settings page (README.md "Settings Requirements").

UI only: reads/writes config/settings.json through
utils.state_manager.load_configuration/save_configuration -- no
recognition/VAD/Whisper logic lives here (CLAUDE.md "Streamlit Rule").
CPU/RAM/GPU info is read-only diagnostic display, not a decision.
"""
from __future__ import annotations

import os
import platform

import torch
import streamlit as st

from app import get_app_state
from utils.state_manager import load_configuration, save_configuration

state = get_app_state()

st.set_page_config(page_title="Settings - Offline Robot", page_icon="🤖")
st.title("Settings")

config = load_configuration()

st.info(
    "Settings are saved to config/settings.json immediately, but services "
    "already running (camera, microphone, Whisper, VAD) read these values "
    "only once at startup. **Restart the app for changes to take effect.**"
)

with st.form("settings_form"):
    st.subheader("Face Recognition Sensitivity")
    face_confidence = st.slider(
        "Minimum match confidence", min_value=0.0, max_value=1.0,
        value=float(config["face_confidence"]), step=0.05,
        help="Lower = stricter matching (larger accepted distance is NOT allowed); "
             "this is the maximum embedding distance accepted as a match.",
    )

    st.subheader("VAD Aggressiveness")
    vad_aggressiveness = st.select_slider(
        "WebRTC VAD aggressiveness (0 = least aggressive, 3 = most)",
        options=[0, 1, 2, 3], value=int(config["vad_aggressiveness"]),
    )

    st.subheader("Whisper Model")
    whisper_models = ["tiny", "base", "small", "medium", "large"]
    current_model = config["whisper_model"] if config["whisper_model"] in whisper_models else "medium"
    whisper_model = st.selectbox(
        "Model size (larger = more accurate, slower)",
        whisper_models, index=whisper_models.index(current_model),
    )

    st.subheader("GPU Acceleration")
    gpu_acceleration = st.checkbox(
        "Use GPU for Whisper when available", value=bool(config["gpu_acceleration"]),
    )

    submitted = st.form_submit_button("💾 Save Settings")
    if submitted:
        config["face_confidence"] = face_confidence
        config["vad_aggressiveness"] = vad_aggressiveness
        config["whisper_model"] = whisper_model
        config["gpu_acceleration"] = gpu_acceleration
        save_configuration(config)
        st.success("Settings saved to config/settings.json.")

st.divider()
st.subheader("System Information")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**CPU**")
    st.write(platform.processor() or platform.machine() or "unknown")
    st.write(f"{os.cpu_count()} logical cores")

with col2:
    st.markdown("**RAM**")
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        phys_pages = os.sysconf("SC_PHYS_PAGES")
        ram_gb = (page_size * phys_pages) / (1024 ** 3)
        st.write(f"{ram_gb:.1f} GB total")
    except (ValueError, OSError, AttributeError):
        st.write("Unavailable on this platform")

with col3:
    st.markdown("**GPU**")
    if torch.cuda.is_available():
        st.write(torch.cuda.get_device_name(0))
        st.write(f"{torch.cuda.device_count()} device(s)")
    else:
        st.write("No CUDA GPU detected")
        st.caption("Whisper will run on CPU regardless of the GPU Acceleration setting above.")
