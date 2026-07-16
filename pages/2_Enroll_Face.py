"""Face enrollment page (README.md "Face Enrollment Requirements").

UI only: captures/uploads an image and a user ID, then hands both to
utils.face_recognition.enroll_face() -- all detection/validation/storage
logic lives there, not here (CLAUDE.md "Streamlit Rule").

Webcam capture reuses camera_service's already-open live feed
(state.latest_raw_frame) instead of opening a second, independent camera
session via st.camera_input(): this machine's webcam does not support two
simultaneous consumers (the same class of device-contention bug found and
fixed for the microphone in Milestone 6), and camera_service is already
continuously capturing frames anyway.
"""
from __future__ import annotations

import cv2
import numpy as np
import streamlit as st

from app import get_app_state
from utils.face_recognition import FaceEnrollmentError, enroll_face, list_enrolled_users

state = get_app_state()

st.set_page_config(page_title="Enroll Face - Offline Robot", page_icon="🤖")
st.title("Enroll Face")

user_id = st.text_input("User ID", placeholder="e.g. natnael")

tab_webcam, tab_upload = st.tabs(["📷 Capture from Webcam", "📁 Upload Image"])

with tab_webcam:
    st.caption("Live feed from the camera service (also used for recognition).")
    if state.latest_frame is not None:
        st.image(cv2.cvtColor(state.latest_frame, cv2.COLOR_BGR2RGB), channels="RGB")
    else:
        st.info("Waiting for camera frames...")

    if st.button("📸 Capture & Save", key="save_webcam"):
        if not user_id.strip():
            st.error("Enter a User ID first.")
        elif state.latest_raw_frame is None:
            st.error("No camera frame available yet.")
        else:
            try:
                path = enroll_face(user_id.strip(), state.latest_raw_frame)
                st.success(f"Enrolled '{user_id.strip()}' -- saved to {path}")
            except FaceEnrollmentError as exc:
                st.error(str(exc))

with tab_upload:
    uploaded = st.file_uploader("Upload a clear, front-facing photo", type=["jpg", "jpeg", "png"])
    if uploaded is not None:
        file_bytes = np.frombuffer(uploaded.getvalue(), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if image is None:
            st.error("Could not read that image file.")
        else:
            st.image(cv2.cvtColor(image, cv2.COLOR_BGR2RGB), channels="RGB", caption="Preview")
            if st.button("💾 Save Enrollment", key="save_upload"):
                if not user_id.strip():
                    st.error("Enter a User ID first.")
                else:
                    try:
                        path = enroll_face(user_id.strip(), image)
                        st.success(f"Enrolled '{user_id.strip()}' -- saved to {path}")
                    except FaceEnrollmentError as exc:
                        st.error(str(exc))

st.subheader("Enrolled Users")
users = list_enrolled_users()
if users:
    st.table(users)
else:
    st.info("No users enrolled yet.")
