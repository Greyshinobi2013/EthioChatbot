import streamlit as st
from utils.vad_handler import set_vad_level
from utils.whisper_utils import load_model

st.title("⚙️ Settings")

tol = st.slider("Tolerance", 0.3, 1.0,
                st.session_state.settings["tolerance"])

model = st.selectbox("Whisper",
                     ["tiny", "base", "small", "medium", "large"])

if st.button("Load Model"):
    load_model(model)
    st.success("Loaded ✅")

vad = st.slider("VAD", 0, 3,
                st.session_state.settings["vad"])

set_vad_level(vad)

interrupt = st.radio("Interrupt",
                     ["Restart Clip", "Continue Playback"])

st.session_state.settings.update({
    "tolerance": tol,
    "whisper": model,
    "vad": vad,
    "interrupt": interrupt
})