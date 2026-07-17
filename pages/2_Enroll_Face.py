"""Face enrollment page for EthioChatbot V2's Streamlit dashboard.

Presentation-layer only: this page collects user input (camera
capture or upload, user ID, priority, preferred language) and shows
the existing enrolled user list, delegating all face detection,
embedding generation, and persistence to utils.face_enrollment, per
ARCHITECTURE.md's rule that Streamlit pages must not contain business
logic.

Camera capture reads frames from the shared utils.camera_service.py
CameraService (the same live feed the Dashboard shows), rather than
opening its own capture device. ARCHITECTURE.md specifies exactly one
camera owner -- CameraService -- and st.camera_input() would violate
that: it acquires a *browser-side* webcam stream via the client's own
getUserMedia(), a second, independent camera acquisition path that
has nothing to do with the server-side OpenCV device CameraService
already owns and is continuously capturing from. On a robot whose
camera is physical hardware attached to the machine running the
service (not necessarily the machine running the browser), that
second path is not just redundant but often cannot work at all --
exactly the symptom reported: the backend camera demonstrably works
(FACE_DETECTED events publishing continuously) while the browser
sits at its own "would like to use your camera" permission prompt for
an unrelated, client-side device.
"""
from __future__ import annotations

import time
from typing import Optional

import numpy as np
import streamlit as st

from app import get_running_application
from utils.face_enrollment import (
    SUPPORTED_LANGUAGES,
    FaceEnrollmentError,
    decode_image_bytes,
    enroll_user,
    load_users,
)

st.set_page_config(page_title="Enroll Face - EthioChatbot V2", page_icon="🧑‍💼")
st.title("Enroll Face")
st.caption("Register a new user, or re-enroll an existing one, with a face image, priority, and preferred language.")

st.subheader("1. Capture or upload a face image")
capture_method = st.radio("Image source", ["Camera (shared with the robot)", "Upload"], horizontal=True)

image_bgr: Optional[np.ndarray] = None

if capture_method == "Camera (shared with the robot)":
    application = get_running_application()
    if application.camera is None:
        st.warning("Camera service is not running yet. Open the Dashboard once to start the full system, then return here.")
    else:
        latest_frame = application.camera.latest_frame

        if "enroll_captured_frame" in st.session_state:
            st.image(
                st.session_state["enroll_captured_frame"][:, :, ::-1],
                channels="RGB",
                caption="Captured photo (ready to enroll)",
                width="stretch",
            )
            image_bgr = st.session_state["enroll_captured_frame"]
            if st.button("Retake"):
                del st.session_state["enroll_captured_frame"]
                st.rerun()
        else:
            if latest_frame is not None:
                st.image(
                    latest_frame[:, :, ::-1],
                    channels="RGB",
                    caption="Live camera feed (from CameraService)",
                    width="stretch",
                )
            else:
                st.info("No camera frame available yet.")

            # Defaults to off, matching pages/1_Dashboard.py's identical
            # pattern: if this defaulted on, the script would keep
            # rerunning itself indefinitely with no user interaction
            # required to stop it, which is wasteful and (observed while
            # verifying this fix) breaks headless test harnesses that
            # wait for a script run to settle.
            auto_refresh = st.checkbox("Auto-refresh preview", value=False)
            if st.button("Capture Photo", type="primary", disabled=latest_frame is None):
                st.session_state["enroll_captured_frame"] = latest_frame.copy()
                st.rerun()
            elif auto_refresh:
                time.sleep(1)
                st.rerun()
else:
    uploaded_file = st.file_uploader("Upload a face image", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        image_bgr = decode_image_bytes(uploaded_file.getvalue())

st.subheader("2. User details")
user_id = st.text_input("User ID", placeholder="e.g. natnael")
priority = st.number_input("Priority (lower number = higher priority)", min_value=0, value=1, step=1)
preferred_language = st.selectbox("Preferred language", SUPPORTED_LANGUAGES)

if st.button("Enroll User", type="primary", disabled=image_bgr is None):
    if not user_id.strip():
        st.error("User ID is required.")
    elif image_bgr is None:
        st.error("Please capture a photo from the camera or upload an image first.")
    else:
        try:
            record = enroll_user(
                user_id=user_id,
                priority=int(priority),
                preferred_language=preferred_language,
                image_bgr=image_bgr,
            )
            st.session_state.pop("enroll_captured_frame", None)
            st.success(
                f"Enrolled '{record.user_id}' successfully "
                f"(priority={record.priority}, language={record.preferred_language})."
            )
        except FaceEnrollmentError as exc:
            st.error(str(exc))

st.divider()
st.subheader("Enrolled Users")
users = load_users()
if not users:
    st.info("No users enrolled yet.")
else:
    st.dataframe(
        [
            {
                "User ID": user.user_id,
                "Priority": user.priority,
                "Preferred Language": user.preferred_language,
                "Image Path": user.image_path,
                "Embedding Path": user.embedding_path,
            }
            for user in sorted(users, key=lambda u: u.priority)
        ],
        width="stretch",
        hide_index=True,
    )
