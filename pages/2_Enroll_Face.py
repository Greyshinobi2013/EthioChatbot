import streamlit as st
import cv2
import numpy as np
from PIL import Image
from utils.face_recognition import add_face

st.title("👤 Enroll Face")

name = st.text_input("Enter Name")

if st.button("Capture"):
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()

    if ret:
        if add_face(frame, name):
            st.success("Saved ✅")
        else:
            st.error("No face detected")

uploaded = st.file_uploader("Upload Image")

if uploaded:
    img = Image.open(uploaded)
    arr = np.array(img)

    if add_face(arr, name):
        st.success("Saved ✅")
    else:
        st.error("No face found")