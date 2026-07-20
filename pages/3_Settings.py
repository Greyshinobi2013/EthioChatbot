"""Settings page for EthioChatbot V3's Streamlit dashboard.

Presentation-layer only: collects setting values and delegates
loading/saving to app.py's AppConfig/load_configuration()/
save_configuration() and load_interaction_mode()/save_interaction_mode(),
per DEVELOPMENT_RULES_V3.md's rule that Streamlit pages must not
contain business logic. Camera/recognition changes take effect the
next time the application starts; the interaction mode also updates
the live running system immediately (mirroring the Dashboard page's
mode switch), since STATE_MACHINE_V3.md's Mode A/B branch is read live
from shared state, not from a value baked in at startup.
"""
from __future__ import annotations

import streamlit as st

from app import (
    INTERACTION_MODES,
    AppConfig,
    ConfigurationError,
    get_running_application,
    load_configuration,
    load_interaction_mode,
    save_configuration,
    save_interaction_mode,
)

st.set_page_config(page_title="Settings - EthioChatbot V3", page_icon=":material/settings:")
st.title("Settings")

try:
    config = load_configuration()
except ConfigurationError as exc:
    st.error(f"Could not load configuration: {exc}")
    st.stop()

st.subheader("Interaction mode")
mode_labels = {"common_dialog": "Mode A - common dialog", "user_specific_dialog": "Mode B - user-specific dialog"}
current_mode = load_interaction_mode()
selected_label = st.segmented_control(
    "Interaction mode",
    options=list(mode_labels.values()),
    default=mode_labels[current_mode],
    label_visibility="collapsed",
)
selected_mode = next((key for key, label in mode_labels.items() if label == selected_label), current_mode)
if selected_mode != current_mode:
    try:
        save_interaction_mode(selected_mode)
        application = get_running_application()
        application.state.set_interaction_mode(selected_mode)
        st.success(f"Interaction mode set to {mode_labels[selected_mode]}.")
    except ConfigurationError as exc:
        st.error(str(exc))

st.caption(f"Persisted to config/interaction_modes.json. Allowed values: {', '.join(INTERACTION_MODES)}.")

st.divider()
st.subheader("Camera")
camera_index = st.number_input("Camera index", min_value=0, value=config.camera_index, step=1)
camera_width = st.number_input("Camera width", min_value=1, value=config.camera_width, step=1)
camera_height = st.number_input("Camera height", min_value=1, value=config.camera_height, step=1)

st.subheader("Recognition")
recognition_interval = st.number_input(
    "Recognition interval (re-recognize an already-tracked face every Nth frame)",
    min_value=1,
    value=config.recognition_interval,
    step=1,
    help="Newly appeared faces are always recognized immediately regardless of this interval.",
)
face_confidence = st.slider(
    "Minimum recognition similarity",
    min_value=0.0,
    max_value=1.0,
    value=config.face_confidence,
    help=(
        "Minimum ArcFace cosine similarity required to accept a match "
        "(higher = stricter). Typical usable range is 0.3-0.5."
    ),
)

st.subheader("Face presence")
face_lost_timeout = st.number_input(
    "Face lost timeout (seconds)",
    min_value=1,
    value=config.face_lost_timeout,
    step=1,
    help="Seconds a recognized user may go unseen before FACE_LOST fires for them.",
)

st.subheader("Servo settings")
yaw_servo_pin = st.number_input(
    "Yaw servo GPIO pin",
    min_value=0,
    value=config.yaw_servo_pin,
    step=1,
    help="GPIO pin the horizontal (yaw) neck servo is wired to.",
)
pitch_servo_pin = st.number_input(
    "Pitch servo GPIO pin",
    min_value=0,
    value=config.pitch_servo_pin,
    step=1,
    help="GPIO pin the vertical (pitch) neck servo is wired to.",
)

st.divider()
if st.button("Save settings", type="primary", icon=":material/save:"):
    updated_config = AppConfig(
        camera_index=int(camera_index),
        camera_width=int(camera_width),
        camera_height=int(camera_height),
        recognition_interval=int(recognition_interval),
        face_confidence=float(face_confidence),
        face_lost_timeout=int(face_lost_timeout),
        yaw_servo_pin=int(yaw_servo_pin),
        pitch_servo_pin=int(pitch_servo_pin),
    )
    try:
        save_configuration(updated_config)
        st.success("Settings saved to config/settings.json. Restart the application for camera/recognition changes to take effect.")
    except ConfigurationError as exc:
        st.error(str(exc))
