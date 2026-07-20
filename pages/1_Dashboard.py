"""Live monitoring dashboard for EthioChatbot V3.

Presentation-layer only, per DEVELOPMENT_RULES_V3.md Rule 24: reads
shared state from the running Application singleton
(app.get_running_application()) and renders it, plus lets the operator
switch interaction modes. Performs no face recognition, priority
sorting, greeting/dialog orchestration, or state transitions itself --
all of that already happens in the services built in utils/.
"""
from __future__ import annotations

import time

import streamlit as st

from app import get_running_application, save_interaction_mode
from utils.logger import DEFAULT_LOG_DIR

st.set_page_config(page_title="Dashboard - EthioChatbot V3", page_icon=":material/smart_toy:", layout="wide")
st.title("EthioChatbot V3 dashboard")

application = get_running_application()
snapshot = application.state.snapshot()

with st.container(horizontal=True):
    st.metric("Current state", snapshot["current_state"], border=True)
    st.metric("Camera status", snapshot["camera_status"], border=True)
    st.metric("Interaction mode", snapshot["interaction_mode"], border=True)
    st.metric("Active users", len(snapshot["active_users"]), border=True)
    st.metric(
        "Playback",
        str(snapshot["playback_status"].get("state", "idle")),
        border=True,
    )

with st.container(horizontal=True):
    head_motion_status = snapshot["head_motion_status"]
    yaw_angle = head_motion_status.get("yaw_angle")
    pitch_angle = head_motion_status.get("pitch_angle")
    st.metric("Yaw position", f"{yaw_angle:.0f}°" if yaw_angle is not None else "—", border=True)
    st.metric("Pitch position", f"{pitch_angle:.0f}°" if pitch_angle is not None else "—", border=True)
    st.metric("Servo status", str(head_motion_status.get("servo_status", "idle")), border=True)

st.divider()

mode_options = {"common_dialog": "Mode A - common dialog", "user_specific_dialog": "Mode B - user-specific dialog"}
current_mode = snapshot["interaction_mode"]
selected_label = st.segmented_control(
    "Interaction mode",
    options=list(mode_options.values()),
    default=mode_options.get(current_mode, mode_options["common_dialog"]),
)
selected_mode = next((key for key, label in mode_options.items() if label == selected_label), current_mode)
if selected_mode != current_mode:
    application.state.set_interaction_mode(selected_mode)
    save_interaction_mode(selected_mode)
    st.rerun()

st.divider()

left, right = st.columns([2, 1])

with left:
    with st.container(border=True):
        st.subheader("Camera feed")
        latest_frame = application.camera.latest_frame if application.camera is not None else None
        if latest_frame is not None:
            # OpenCV frames are BGR; Streamlit's image() expects RGB.
            st.image(latest_frame[:, :, ::-1], channels="RGB", width="stretch")
        else:
            st.info("No camera frame available yet.")

    with st.container(border=True):
        st.subheader("Greeting queue")
        greeting_queue = snapshot["greeting_queue"]
        if not greeting_queue:
            st.caption("No greeting queue built for the current session.")
        else:
            st.write(" → ".join(greeting_queue))

with right:
    with st.container(border=True):
        st.subheader("Detected users (this frame)")
        detected_users = snapshot["detected_users"]
        if not detected_users:
            st.caption("No enrolled users currently detected.")
        else:
            st.write(", ".join(detected_users))

    with st.container(border=True):
        st.subheader("Active users")
        active_users = snapshot["active_users"]
        if not active_users:
            st.caption("No recognized users currently present.")
        else:
            st.dataframe(
                [
                    {
                        "User ID": user_id,
                        "Priority": info["priority"],
                        "Language": info["preferred_language"],
                        "Greeted": info["greeted"],
                        "Last seen": time.strftime("%H:%M:%S", time.localtime(info["last_seen"])),
                    }
                    for user_id, info in sorted(active_users.items(), key=lambda item: item[1]["priority"])
                ],
                width="stretch",
                hide_index=True,
            )
        # Replays greetings + dialogs for everyone currently visible,
        # without touching recognition, presence, enrollment, priority,
        # or language data -- see fsm.py's RESTART_GREETINGS transitions
        # and greeting_manager.py's handling of it. Per
        # STATE_MACHINE_V3.md's MONITORING and PAUSED_DIALOG "Allowed
        # Events" sections, RESTART_GREETINGS is only a valid FSM
        # transition from exactly those two states -- enabling the
        # button anywhere else would let an operator trigger a
        # transition the FSM immediately rejects.
        restart_enabled = (snapshot["current_state"] == "MONITORING" and bool(active_users)) or snapshot[
            "current_state"
        ] == "PAUSED_DIALOG"
        if st.button(
            "Restart Greetings",
            icon=":material/replay:",
            disabled=not restart_enabled,
        ):
            application.event_bus.publish("RESTART_GREETINGS", {})
            st.rerun()

        # Dashboard-only operator override, per HEAD_MOTION_SPECIFICATION_V3.md
        # / SYSTEM_ARCHITECTURE_V3.md's Dashboard control list: recenters
        # both servos and stops any in-progress surveillance scan.
        if st.button("Center Head", icon=":material/adjust:"):
            if application.head_motion is not None:
                application.head_motion.center_head()
            st.rerun()

    with st.container(border=True):
        st.subheader("Playback status")
        playback_status = snapshot["playback_status"]
        st.json(playback_status, expanded=False)
        # Per the Dialog Interruption Framework, this must go through
        # the FSM (INTERRUPT_DIALOG/RESUME_DIALOG), not call
        # PlaybackService directly -- that would desync the FSM's
        # state from actual playback state, and would let greetings
        # be paused too (the FSM only accepts these events from the
        # two dialog states, never from PLAY_GREETINGS).
        if snapshot["current_state"] in ("PLAY_COMMON_DIALOG", "PLAY_USER_DIALOGS"):
            if st.button("Pause dialog", icon=":material/pause:"):
                application.event_bus.publish("INTERRUPT_DIALOG", {})
                st.rerun()
        elif snapshot["current_state"] == "PAUSED_DIALOG":
            if st.button("Resume dialog", icon=":material/play_arrow:"):
                application.event_bus.publish("RESUME_DIALOG", {})
                st.rerun()

st.divider()

with st.container(border=True):
    st.subheader("Recent logs")
    log_file = DEFAULT_LOG_DIR / "ethiochatbot.log"
    if log_file.exists():
        log_lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        st.code("\n".join(log_lines[-50:]) or "(log file is empty)", language="log")
    else:
        st.info("No log file found yet.")

auto_refresh = st.checkbox("Auto-refresh every 2 seconds", value=False)
if st.button("Refresh now", icon=":material/refresh:") or auto_refresh:
    if auto_refresh:
        time.sleep(2)
    st.rerun()
