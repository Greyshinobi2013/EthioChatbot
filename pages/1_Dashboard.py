"""Monitoring dashboard (README.md "Dashboard Requirements").

UI only: reads shared AppState and the log file, calls no service logic
directly (CLAUDE.md "Streamlit Rule" -- business logic stays in utils/).
"""
from __future__ import annotations

import time

import cv2
import streamlit as st

from app import get_app_state
from utils.logger import LOG_FILE, read_recent_logs

state = get_app_state()

st.set_page_config(page_title="Dashboard - Offline Robot", page_icon="🤖")
st.title("Dashboard")

auto_refresh = st.checkbox("Auto-refresh (every 2s)", value=False)
if st.button("🔄 Refresh now"):
    st.rerun()

snapshot = state.snapshot()

st.subheader("Status")
col1, col2, col3, col4 = st.columns(4)
col1.metric("System Status", snapshot["system_status"])
col2.metric("Current State", snapshot["current_state"])
col3.metric("Recognized User", snapshot["recognized_user"] or "-")
col4.metric("Current Language", snapshot["current_language"] or "-")

col5, col6, col7, col8 = st.columns(4)
col5.metric("Camera Status", snapshot["camera_status"])
col6.metric("Microphone Status", snapshot["microphone_status"])
col7.metric("Wake Word Status", snapshot["wake_word_status"])
col8.metric("VAD Status", snapshot["vad_status"])

col9, col10 = st.columns(2)
col9.metric("Playback Status", snapshot["playback_status"])
col10.metric("Conversation Status", snapshot["conversation_status"])

st.subheader("Live Webcam Feed")
st.caption("Bounding boxes: green = recognized user, red = unrecognized face")
if state.latest_frame is not None:
    st.image(cv2.cvtColor(state.latest_frame, cv2.COLOR_BGR2RGB), channels="RGB")
else:
    st.info("Waiting for camera frames...")

st.subheader("System Logs")
log_lines = read_recent_logs(200)
st.text_area("Recent log entries", value="\n".join(log_lines), height=300, disabled=True)
st.caption(f"Log file: `{LOG_FILE.resolve()}`")

with st.expander("Configuration"):
    st.json(state.config)

with st.expander("Full runtime state"):
    st.json(snapshot)

if auto_refresh:
    time.sleep(2)
    st.rerun()
