import streamlit as st
import cv2
from utils.face_recognition import recognize_face
from utils.audio_listener import record_and_transcribe

st.title("📊 Dashboard")

# CAMERA
if st.checkbox("Start Camera"):
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()

    if ret:
        locs, names = recognize_face(
            frame,
            st.session_state.settings["tolerance"]
        )

        for ((top, right, bottom, left), name) in zip(locs, names):
            cv2.rectangle(frame, (left, top), (right, bottom), (0,255,0), 2)
            cv2.putText(frame, name, (left, top-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

            st.session_state.session["user"] = name

        st.image(frame, channels="BGR")

# VOICE
st.subheader("🎤 Voice Input")

if st.button("Start Listening"):
    text = record_and_transcribe()
    st.session_state.session["last_text"] = text

st.write("Last Speech:", st.session_state.session["last_text"])

# STATE
st.write(st.session_state.session)

if st.button("Trigger Greeting"):
    st.session_state.session["scenario"] = "greeting"