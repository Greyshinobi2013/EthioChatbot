# pages/1_Dashboard.py

import cv2
import json
import logging
from pathlib import Path

import streamlit as st

# ==========================================================
# Backend Imports
# ==========================================================

from utils.face_recognition import (
    load_faces,
    detect_face,
    match_face
)

from utils.vad_handler import (
    start_vad,
    is_speech,
    monitor_interruptions
)

from utils.whisper_utils import (
    load_model,
    transcribe_audio,
    detect_wake_word
)

from utils.playback import (
    play_audio,
    pause_audio,
    resume_audio,
    restart_audio,
    notify_user
)

# ==========================================================
# Configuration
# ==========================================================

CONFIG_PATH = Path("config/dialog_config.json")
KNOWN_FACES_DIR = "faces"

# ==========================================================
# Logging
# ==========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# ==========================================================
# Session State Initialization
# ==========================================================

DEFAULTS = {
    "system_enabled": True,
    "identified_language": "Unknown",
    "vad_state": "Idle",
    "recognized_user": "Unknown",
    "selected_scenario": None,
    "logs": [],
    "known_faces": None,
    "whisper_model": None
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ==========================================================
# Helper Functions
# ==========================================================

def add_log(message: str):
    """
    Add dashboard log entry.
    """

    logger.info(message)

    st.session_state.logs.insert(
        0,
        message
    )

    st.session_state.logs = (
        st.session_state.logs[:200]
    )


def load_scenarios():

    try:

        with open(
            CONFIG_PATH,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as error:

        add_log(
            f"Scenario load error: {error}"
        )

        return {}


def get_scenario_options():

    config = load_scenarios()

    options = []

    for language, scenarios in config.items():

        if isinstance(scenarios, dict):

            for scenario_name in scenarios:

                options.append(
                    f"{language}|{scenario_name}"
                )

    return options


def get_scenario_audio(selected_name):

    try:

        language, scenario = (
            selected_name.split("|")
        )

        config = load_scenarios()

        return config[
            language.strip()
        ][
            scenario.strip()
        ]

    except Exception:
        return None


# ==========================================================
# Backend Initialization
# ==========================================================

if st.session_state.known_faces is None:

    try:

        st.session_state.known_faces = (
            load_faces(KNOWN_FACES_DIR)
        )

        add_log(
            "Known faces loaded."
        )

    except Exception as e:

        add_log(
            f"Face database error: {e}"
        )

if st.session_state.whisper_model is None:

    try:

        st.session_state.whisper_model = (
            load_model("medium")
        )

        add_log(
            "Whisper model loaded."
        )

    except Exception as e:

        add_log(
            f"Whisper load error: {e}"
        )

try:

    start_vad()

except Exception as e:

    add_log(
        f"VAD initialization failed: {e}"
    )

# ==========================================================
# Interruption Handling Callback
# ==========================================================

def interruption_callback():

    try:

        pause_audio()

        st.session_state.vad_state = (
            "Speaking"
        )

        add_log(
            "Interruption detected."
        )

        notify_user(
            "Please wait"
        )

    except Exception as e:

        add_log(
            f"Interrupt error: {e}"
        )

# Start VAD monitoring
try:
    monitor_interruptions(
        interruption_callback
    )
except Exception:
    pass

# ==========================================================
# Header
# ==========================================================

st.title("Dashboard")

st.caption(
    "Monitor live feed, system status, and scenarios."
)

# ==========================================================
# Live Webcam Feed
# ==========================================================

st.subheader("Live Webcam Feed")

camera_placeholder = st.empty()

try:

    cap = cv2.VideoCapture(0)

    success, frame = cap.read()

    if success:

        faces = detect_face(frame)

        for detected in faces:

            bbox = detected.get("bbox")
            embedding = detected.get(
                "embedding"
            )

            if bbox is None:
                continue

            x, y, w, h = bbox

            user_name = match_face(
                embedding,
                st.session_state.known_faces
            )

            if user_name:

                if (
                    user_name
                    != st.session_state.recognized_user
                ):

                    add_log(
                        f"Face recognized: "
                        f"{user_name}"
                    )

                st.session_state.recognized_user = (
                    user_name
                )

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    user_name,
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        camera_placeholder.image(
            rgb,
            use_container_width=True
        )

    else:

        st.warning(
            "Unable to access webcam."
        )

    cap.release()

except Exception as e:

    st.error(
        f"Camera Error: {e}"
    )

# ==========================================================
# Wake Word / Language Detection
# ==========================================================

try:

    audio_file = "audio/input.wav"

    text = transcribe_audio(
        audio_file,
        st.session_state.whisper_model
    )

    wake_word = detect_wake_word(
        text,
        [
            "hello",
            "hey assistant",
            "computer",
            "selam"
        ]
    )

    if wake_word:

        st.session_state.identified_language = (
            wake_word
        )

        add_log(
            f"Wake word detected: "
            f"{wake_word}"
        )

except Exception:
    pass

# ==========================================================
# VAD Status
# ==========================================================

try:

    dummy_audio_chunk = b""

    speech_detected = is_speech(
        dummy_audio_chunk
    )

    if speech_detected:

        st.session_state.vad_state = (
            "Speaking"
        )

    else:

        st.session_state.vad_state = (
            "Idle"
        )

except Exception:
    pass

# ==========================================================
# Status Indicators
# ==========================================================

col1, col2, col3 = st.columns(3)

with col1:

    st.markdown(
        "### System Status"
    )

    if st.session_state.system_enabled:
        st.success("ON")
    else:
        st.error("OFF")

    if st.button(
        "Toggle System",
        use_container_width=True
    ):

        st.session_state.system_enabled = (
            not st.session_state.system_enabled
        )

        add_log(
            f"System {'ON' if st.session_state.system_enabled else 'OFF'}"
        )

with col2:

    st.markdown(
        "### Identified Language"
    )

    st.info(
        st.session_state.identified_language
    )

with col3:

    st.markdown(
        "### VAD State"
    )

    if st.session_state.vad_state == "Speaking":
        st.success("Active")
    else:
        st.warning("Idle")

# ==========================================================
# Scenario Controls
# ==========================================================

st.markdown("---")

st.subheader(
    "Scenario Selector"
)

scenario_options = (
    get_scenario_options()
)

selected_scenario = st.selectbox(
    "Available Scenarios",
    scenario_options
    if scenario_options
    else ["No Scenarios"]
)

col_play, col_pause, col_resume, col_restart = (
    st.columns(4)
)

with col_play:

    if st.button(
        "▶ Start",
        use_container_width=True
    ):

        try:

            scenario_audio = (
                get_scenario_audio(
                    selected_scenario
                )
            )

            if scenario_audio:

                play_audio(
                    scenario_audio
                )

                add_log(
                    f"Scenario started: "
                    f"{selected_scenario}"
                )

            else:

                notify_user(
                    "Please wait"
                )

                add_log(
                    "Scenario audio missing."
                )

        except Exception as e:

            add_log(
                f"Playback error: {e}"
            )

with col_pause:

    if st.button(
        "⏸ Pause",
        use_container_width=True
    ):

        try:

            pause_audio()

            add_log(
                "Playback paused."
            )

        except Exception as e:

            add_log(
                f"Pause error: {e}"
            )

with col_resume:

    if st.button(
        "▶ Resume",
        use_container_width=True
    ):

        try:

            resume_audio()

            add_log(
                "Playback resumed."
            )

        except Exception as e:

            add_log(
                f"Resume error: {e}"
            )

with col_restart:

    if st.button(
        "⟲ Restart",
        use_container_width=True
    ):

        try:

            scenario_audio = (
                get_scenario_audio(
                    selected_scenario
                )
            )

            if scenario_audio:

                restart_audio(
                    scenario_audio
                )

                add_log(
                    "Scenario restarted."
                )

        except Exception as e:

            add_log(
                f"Restart error: {e}"
            )

# ==========================================================
# System Log
# ==========================================================

st.markdown("---")

st.subheader("System Log")

st.text_area(
    "Events",
    value="\n".join(
        st.session_state.logs
    ),
    height=250,
    disabled=True
)

# ==========================================================
# Footer Status
# ==========================================================

st.caption(
    f"Recognized User: "
    f"{st.session_state.recognized_user}"
)