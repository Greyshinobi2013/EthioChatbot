import streamlit as st
import json
from pathlib import Path

import torch

# --------------------------------------------------
# Configuration
# --------------------------------------------------

SETTINGS_FILE = Path("config/settings.json")

DEFAULT_SETTINGS = {
    "recognition_threshold": 0.5,
    "vad_aggressiveness": 1,
    "whisper_model": "base",
    "gpu_enabled": False
}


# --------------------------------------------------
# Helper Functions
# --------------------------------------------------

def load_settings():

    if SETTINGS_FILE.exists():

        try:
            with open(
                SETTINGS_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                return json.load(f)

        except Exception:
            return DEFAULT_SETTINGS

    return DEFAULT_SETTINGS


def save_settings(settings):

    with open(
        SETTINGS_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            settings,
            f,
            indent=4
        )


# --------------------------------------------------
# Load Settings
# --------------------------------------------------

settings = load_settings()

if "recognition_threshold" not in st.session_state:
    st.session_state.recognition_threshold = settings[
        "recognition_threshold"
    ]

if "vad_aggressiveness" not in st.session_state:
    st.session_state.vad_aggressiveness = settings[
        "vad_aggressiveness"
    ]

if "whisper_model" not in st.session_state:
    st.session_state.whisper_model = settings[
        "whisper_model"
    ]

if "gpu_enabled" not in st.session_state:
    st.session_state.gpu_enabled = settings[
        "gpu_enabled"
    ]

# --------------------------------------------------
# Page UI
# --------------------------------------------------

st.title("⚙️ Settings")

st.markdown(
    "Configure face recognition, VAD, Whisper, "
    "and hardware acceleration options."
)

# --------------------------------------------------
# Face Recognition
# --------------------------------------------------

st.subheader("Face Recognition")

threshold = st.slider(
    "Recognition Sensitivity",
    min_value=0.0,
    max_value=1.0,
    value=float(
        st.session_state.recognition_threshold
    ),
    step=0.01,
    help="Lower values are stricter."
)

# --------------------------------------------------
# VAD
# --------------------------------------------------

st.subheader("Voice Activity Detection")

vad = st.slider(
    "VAD Aggressiveness",
    min_value=0,
    max_value=3,
    value=int(
        st.session_state.vad_aggressiveness
    ),
    help="Higher values filter more noise."
)

# --------------------------------------------------
# Whisper
# --------------------------------------------------

st.subheader("Speech Recognition")

whisper_model = st.selectbox(
    "Whisper Model",
    [
        "tiny",
        "base",
        "small",
        "medium",
        "large"
    ],
    index=[
        "tiny",
        "base",
        "small",
        "medium",
        "large"
    ].index(
        st.session_state.whisper_model
    )
)

# --------------------------------------------------
# GPU
# --------------------------------------------------

st.subheader("Acceleration")

gpu_enabled = st.toggle(
    "Enable GPU Acceleration",
    value=st.session_state.gpu_enabled
)

# --------------------------------------------------
# Hardware Info
# --------------------------------------------------

st.divider()

st.subheader("Hardware Usage")

try:

    import psutil

    cpu_usage = psutil.cpu_percent()

    ram_usage = psutil.virtual_memory()

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "CPU Usage",
            f"{cpu_usage}%"
        )

    with col2:
        st.metric(
            "RAM Usage",
            f"{ram_usage.percent}%"
        )

except Exception:
    st.warning(
        "Unable to retrieve hardware information."
    )

try:
    gpu_available = torch.cuda.is_available()
    st.write(f"GPU Available: {'✅ Yes' if gpu_available else '❌ No'}")
except Exception:
    st.warning(
        "Unable to check GPU availability."
    )
# --------------------------------------------------
# Save Settings
# --------------------------------------------------

st.divider()

if st.button(
    "💾 Save Settings",
    use_container_width=True
):

    st.session_state.recognition_threshold = (
        threshold
    )

    st.session_state.vad_aggressiveness = (
        vad
    )

    st.session_state.whisper_model = (
        whisper_model
    )

    st.session_state.gpu_enabled = (
        gpu_enabled
    )

    save_settings(
        {
            "recognition_threshold": threshold,
            "vad_aggressiveness": vad,
            "whisper_model": whisper_model,
            "gpu_enabled": gpu_enabled
        }
    )

    st.success(
        "Settings saved successfully."
    )