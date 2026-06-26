import streamlit as st
import cv2
import requests
import numpy as np
from PIL import Image

st.set_page_config(page_title="EthioChatbot MVP", layout="wide")

st.title("EthioChatbot: Offline Voice Assistant")

col1, col2 = st.columns([2, 1])

with col1:
    st.header("Live Feed")
    run = st.checkbox('Run Camera', value=True)
    FRAME_WINDOW = st.image([])
    camera = cv2.VideoCapture(0)

    while run:
        _, frame = camera.read()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # In a real app, we would throttle requests to backend
        # For demo, just show the feed
        FRAME_WINDOW.image(frame)
        
        if not run:
            break

with col2:
    st.header("Controls")
    
    name = st.text_input("User Name")
    uploaded_files = st.file_uploader("Upload 5 Enrollment Images", accept_multiple_files=True)
    
    if st.button("Enroll User"):
        if name and uploaded_files:
            files = [("files", (f.name, f.getvalue())) for f in uploaded_files]
            data = {"name": name}
            resp = requests.post("http://localhost:8000/enroll", data=data, files=files)
            st.success(resp.json()["status"])
    
    st.divider()
    
    if st.button("Forget All"):
        # Placeholder for data clearing
        st.warning("Feature not implemented yet.")

    st.header("Logs")
    log_area = st.empty()
    # Placeholder for displaying greeting queue or events
