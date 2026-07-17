"""Live monitoring dashboard for EthioChatbot V2.

Presentation-layer only: reads shared state from the running
Application singleton (app.get_running_application()) and renders it.
Performs no face recognition, speech recognition, scenario matching,
playback handling, or state transitions itself, per ARCHITECTURE.md's
restriction on Streamlit pages containing business logic -- all of
that already happened in the services built in Milestones 3-10.
"""
from __future__ import annotations

import time

import streamlit as st

from app import get_running_application
from utils.logger import DEFAULT_LOG_DIR

st.set_page_config(page_title="Dashboard - EthioChatbot V2", page_icon="🤖", layout="wide")
st.title("EthioChatbot V2 Dashboard")

application = get_running_application()
snapshot = application.state.snapshot()

status_cols = st.columns(5)
status_cols[0].metric("Current State", snapshot["current_state"])
status_cols[1].metric("Current Language", snapshot["current_language"] or "-")
status_cols[2].metric("Camera Status", snapshot["camera_status"])
status_cols[3].metric("Playback Status", snapshot["playback_status"])
status_cols[4].metric("Wake Word Status", snapshot["wake_word_status"])

st.divider()

left, right = st.columns([2, 1])

with left:
    st.subheader("Camera Feed")
    latest_frame = application.camera.latest_frame if application.camera is not None else None
    if latest_frame is not None:
        # OpenCV frames are BGR; Streamlit's image() expects RGB.
        st.image(latest_frame[:, :, ::-1], channels="RGB", width="stretch")
    else:
        st.info("No camera frame available yet.")

with right:
    st.subheader("Active Users")
    active_users = snapshot["active_users"]
    if not active_users:
        st.info("No recognized users currently visible.")
    else:
        st.dataframe(
            [
                {
                    "User ID": user_id,
                    "Priority": info["priority"],
                    "Preferred Language": info["preferred_language"],
                    "Last Seen": time.strftime("%H:%M:%S", time.localtime(info["last_seen"])),
                }
                for user_id, info in sorted(active_users.items(), key=lambda item: item[1]["priority"])
            ],
            width="stretch",
            hide_index=True,
        )

st.divider()

st.subheader("Recent Logs")
log_file = DEFAULT_LOG_DIR / "ethiochatbot.log"
if log_file.exists():
    log_lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    st.code("\n".join(log_lines[-50:]) or "(log file is empty)", language="log")
else:
    st.info("No log file found yet.")

st.divider()
auto_refresh = st.checkbox("Auto-refresh every 2 seconds", value=False)
if st.button("Refresh now") or auto_refresh:
    if auto_refresh:
        time.sleep(2)
    st.rerun()
