"""Face enrollment page for EthioChatbot V2's Streamlit dashboard.

Presentation-layer only: this page collects user input (webcam
capture or upload, user ID, priority, preferred language) and shows
the existing enrolled user list, delegating all face detection,
embedding generation, and persistence to utils.face_enrollment, per
ARCHITECTURE.md's rule that Streamlit pages must not contain business
logic.
"""
from __future__ import annotations

from typing import Optional

import streamlit as st

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
capture_method = st.radio("Image source", ["Webcam", "Upload"], horizontal=True)

image_bytes: Optional[bytes] = None
if capture_method == "Webcam":
    camera_photo = st.camera_input("Take a photo")
    if camera_photo is not None:
        image_bytes = camera_photo.getvalue()
else:
    uploaded_file = st.file_uploader("Upload a face image", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        image_bytes = uploaded_file.getvalue()

st.subheader("2. User details")
user_id = st.text_input("User ID", placeholder="e.g. natnael")
priority = st.number_input("Priority (lower number = higher priority)", min_value=0, value=1, step=1)
preferred_language = st.selectbox("Preferred language", SUPPORTED_LANGUAGES)

if st.button("Enroll User", type="primary", disabled=image_bytes is None):
    if not user_id.strip():
        st.error("User ID is required.")
    elif image_bytes is None:
        st.error("Please capture or upload a face image first.")
    else:
        try:
            image = decode_image_bytes(image_bytes)
            record = enroll_user(
                user_id=user_id,
                priority=int(priority),
                preferred_language=preferred_language,
                image_bgr=image,
            )
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
