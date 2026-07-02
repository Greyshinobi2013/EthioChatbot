import streamlit as st
import time
from datetime import datetime

from streamlit_webrtc import webrtc_streamer, AudioProcessorBase

from core.bot_controller import BotController
from core.constants import BotState
from core.webrtc_audio import AudioBuffer

# ─────────────────────────────────────────────

st.set_page_config(layout="wide")

# ─────────────────────────────────────────────
# SESSION

if "bot" not in st.session_state:
    st.session_state.bot = None

if "running" not in st.session_state:
    st.session_state.running = False

if "state" not in st.session_state:
    st.session_state.state = BotState.IDLE

if "face" not in st.session_state:
    st.session_state.face = "No face"

if "transcript" not in st.session_state:
    st.session_state.transcript = ""

# ─────────────────────────────────────────────
# AUDIO PROCESSOR

class AudioProcessor(AudioProcessorBase):

    def __init__(self):
        self.buffer = AudioBuffer()

    def recv(self, frame):
        self.buffer.add_audio(frame)
        return frame

# ─────────────────────────────────────────────
# BOT CONTROL

def start():

    bot = BotController()

    def on_state(s):
        st.session_state.state = s

    def on_face(n, c):
        st.session_state.face = n

    def on_trans(t):
        st.session_state.transcript = t

    bot.on_state_change = on_state
    bot.on_face_detected = on_face
    bot.on_transcript = on_trans

    bot.start()

    st.session_state.bot = bot
    st.session_state.running = True


def stop():

    if st.session_state.bot:
        st.session_state.bot.stop()

    st.session_state.running = False
    st.session_state.bot = None

# ─────────────────────────────────────────────
# SIDEBAR

with st.sidebar:

    st.title("🤖 Ethiobot")

    if not st.session_state.running:
        if st.button("Start"):
            start()
    else:
        if st.button("Stop"):
            stop()

    st.metric("State", st.session_state.state.name)
    st.metric("Face", st.session_state.face)

# ─────────────────────────────────────────────
# MAIN

st.title("Ethiobot Station")

# ✅ MICROPHONE (REAL BROWSER PERMISSION)

st.subheader("🎤 Microphone")

audio_ctx = webrtc_streamer(
    key="audio",
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False}
)

# ✅ SEND AUDIO TO BOT

if (
    audio_ctx.audio_processor
    and st.session_state.bot
):

    chunk = audio_ctx.audio_processor.buffer.get_audio_chunk()

    st.session_state.bot.feed_audio(chunk)


# ✅ CAMERA STREAM (OPTIONAL)

st.subheader("📷 Camera")

webrtc_streamer(
    key="video",
    media_stream_constraints={"video": True, "audio": False}
)

# ✅ TRANSCRIPT

st.subheader("Transcript")

st.code(st.session_state.transcript)

# AUTO REFRESH

if st.session_state.running:
    time.sleep(0.2)
    st.rerun()