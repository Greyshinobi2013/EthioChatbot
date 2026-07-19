"""Face enrollment page for EthioChatbot V3's Streamlit dashboard.

Presentation-layer only: collects user input (camera capture or
upload for each of the three required angles, user ID, priority,
preferred language) and shows the existing enrolled user list,
delegating all detection, alignment, embedding generation, and
persistence to utils.face_enrollment, per DEVELOPMENT_RULES_V3.md's
rule that Streamlit pages must not contain business logic.

Camera capture reads frames from the shared utils.camera_service.py
CameraService (the same live feed the Dashboard shows) rather than
opening a second, independent browser-side camera stream -- there is
exactly one camera owner, CameraService.
"""
from __future__ import annotations

import time
from typing import Optional

import numpy as np
import streamlit as st

from app import get_running_application
from utils.face_enrollment import (
    ENROLLMENT_ANGLES,
    SUPPORTED_LANGUAGES,
    FaceEnrollmentError,
    decode_image_bytes,
    enroll_user,
    load_users,
)

st.set_page_config(page_title="Enroll face - EthioChatbot V3", page_icon=":material/person_add:")
st.title("Enroll face")
st.caption(
    "Register a new user, or re-enroll an existing one, with three face images "
    "(front, left profile, right profile), a priority, and a preferred language."
)

ANGLE_LABELS = {"front": "Front face", "left": "Left profile", "right": "Right profile"}


def _capture_angle(angle: str, application) -> Optional[np.ndarray]:
    """Render the capture/upload UI for one enrollment angle.

    Returns the captured BGR image for this angle, from session state
    if already captured this run, else None.
    """
    state_key = f"enroll_{angle}_frame"
    st.markdown(f"**{ANGLE_LABELS[angle]}**")

    source = st.radio(
        "Image source", ["Camera", "Upload"], horizontal=True, key=f"enroll_{angle}_source", label_visibility="collapsed"
    )

    if source == "Upload":
        uploaded_file = st.file_uploader(
            "Upload an image", type=["jpg", "jpeg", "png"], key=f"enroll_{angle}_upload", label_visibility="collapsed"
        )
        if uploaded_file is not None:
            st.session_state[state_key] = decode_image_bytes(uploaded_file.getvalue())
        return st.session_state.get(state_key)

    if application.camera is None:
        st.warning("Camera service is not running yet. Open the Dashboard once to start the full system.")
        return st.session_state.get(state_key)

    if state_key in st.session_state:
        st.image(
            st.session_state[state_key][:, :, ::-1],
            channels="RGB",
            caption=f"Captured ({ANGLE_LABELS[angle]})",
            width="stretch",
        )
        if st.button("Retake", key=f"enroll_{angle}_retake", icon=":material/replay:"):
            del st.session_state[state_key]
            st.rerun()
    else:
        latest_frame = application.camera.latest_frame
        if latest_frame is not None:
            st.image(latest_frame[:, :, ::-1], channels="RGB", caption="Live camera feed", width="stretch")
            if st.button("Capture photo", key=f"enroll_{angle}_capture", icon=":material/photo_camera:", type="primary"):
                st.session_state[state_key] = latest_frame.copy()
                st.rerun()
        else:
            st.info("No camera frame available yet.")

    return st.session_state.get(state_key)


application = get_running_application()

st.subheader("1. Capture three face images")
angle_images = {}
columns = st.columns(3)
for column, angle in zip(columns, ENROLLMENT_ANGLES):
    with column:
        angle_images[angle] = _capture_angle(angle, application)

st.subheader("2. User details")
user_id = st.text_input("User ID", placeholder="e.g. natnael")
priority = st.number_input("Priority (lower number = higher priority)", min_value=0, value=1, step=1)
preferred_language = st.selectbox("Preferred language", SUPPORTED_LANGUAGES)

all_captured = all(angle_images[angle] is not None for angle in ENROLLMENT_ANGLES)

if st.button("Enroll user", type="primary", disabled=not all_captured):
    if not user_id.strip():
        st.error("User ID is required.")
    else:
        try:
            record = enroll_user(
                user_id=user_id,
                priority=int(priority),
                preferred_language=preferred_language,
                front_image_bgr=angle_images["front"],
                left_image_bgr=angle_images["left"],
                right_image_bgr=angle_images["right"],
            )
            for angle in ENROLLMENT_ANGLES:
                st.session_state.pop(f"enroll_{angle}_frame", None)

            # enroll_user() only writes to disk; the live FaceRecognizer
            # CameraService is using loaded its embedding cache once at
            # startup. CameraService holds the exact same FaceRecognizer
            # instance (not a copy), so refreshing it here immediately
            # updates what the live camera pipeline recognizes.
            if application.recognizer is not None:
                application.recognizer.reload_embeddings()

            st.success(
                f"Enrolled '{record.user_id}' successfully "
                f"(priority={record.priority}, language={record.preferred_language})."
            )
            time.sleep(1)
            st.rerun()
        except FaceEnrollmentError as exc:
            st.error(str(exc))

if not all_captured:
    st.caption("Capture or upload all three angles above to enable enrollment.")

st.divider()
st.subheader("Enrolled users")
users = load_users()
if not users:
    st.info("No users enrolled yet.")
else:
    st.dataframe(
        [
            {
                "User ID": user.user_id,
                "Priority": user.priority,
                "Language": user.preferred_language,
                "Greeting audio": user.greeting_audio,
                "Dialog audio": user.dialog_audio,
            }
            for user in sorted(users, key=lambda u: u.priority)
        ],
        width="stretch",
        hide_index=True,
    )
