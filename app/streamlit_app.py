"""
Streamlit dashboard for the offline multimodal chatbot.

Run with:
    streamlit run app/streamlit_app.py

Page layout
-----------
- Sidebar: navigation between Dashboard / Enroll Face / Manage Scenarios / Settings.
- Dashboard: live webcam feed with face-recognition overlay, current
  session status, wake-word test button, and dialog controls.
- Enroll Face: webcam capture or photo upload -> encode -> store.
- Manage Scenarios: read-only view of dialog_config.json scenarios,
  with a JSON editor for advanced users.
- Settings: tunable recognition/VAD parameters for this session.
"""

from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from app.core.bootstrap import build_face_engine, build_orchestrator, build_transcriber
from app.core.config import DIALOG_CONFIG_PATH, SETTINGS, get_logger, load_dialog_config
from app.core.face_engine import draw_matches
from app.core.orchestrator import SessionState

logger = get_logger(__name__)

st.set_page_config(
    page_title="Offline Multimodal Chatbot",
    page_icon="🗣️",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Cached resource construction (expensive: loads dlib + Whisper + pygame)
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Loading face recognition models...")
def get_face_engine():
    return build_face_engine()


@st.cache_resource(show_spinner="Loading Whisper speech model...")
def get_transcriber():
    return build_transcriber()


@st.cache_resource(show_spinner="Starting chatbot session...")
def get_orchestrator():
    return build_orchestrator()


def get_orchestrator_safe():
    """UI-facing wrapper: returns (orchestrator, error_message). Keeps
    the page rendering even if a hard dependency (pygame) is missing,
    so the rest of the dashboard (settings, scenario viewer) still
    works for setup/debugging purposes."""
    try:
        return get_orchestrator(), None
    except Exception as exc:
        return None, str(exc)


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

st.sidebar.title("🗣️ Offline Chatbot")
page = st.sidebar.radio(
    "Go to",
    ["Dashboard", "Enroll Face", "Manage Scenarios", "Settings"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "All processing (face recognition, speech recognition, audio playback) "
    "runs locally on this machine. No data leaves your network."
)


# ---------------------------------------------------------------------------
# Page: Dashboard
# ---------------------------------------------------------------------------

def render_dashboard():
    st.title("Dashboard")
    orchestrator, error = get_orchestrator_safe()

    if orchestrator is None:
        st.error(f"Chatbot session could not start: {error}")
        st.stop()

    col_video, col_status = st.columns([3, 2])

    with col_video:
        st.subheader("Webcam feed")
        run_camera = st.toggle("Enable camera + recognition", value=False, key="dash_run_camera")
        frame_slot = st.empty()

        if run_camera:
            if orchestrator.face_engine is None:
                st.error(
                    "Face recognition isn't available. Check that dlib's model "
                    "files are installed (see README), then reload this page."
                )
            else:
                import cv2

                cap = cv2.VideoCapture(0)
                # Bounded loop, not `while True`: Streamlit reruns the script on
                # every widget interaction, so we capture a short burst of
                # frames per run rather than blocking the page forever. The
                # toggle staying on will trigger the next rerun automatically.
                frames_to_capture = 30
                for _ in range(frames_to_capture):
                    ok, frame = cap.read()
                    if not ok:
                        st.warning("Could not read from webcam.")
                        break
                    matches = orchestrator.process_frame(frame)
                    annotated = draw_matches(frame, matches)
                    frame_slot.image(annotated, channels="BGR")
                    time.sleep(0.03)
                cap.release()
                st.rerun()
        else:
            frame_slot.info("Camera is off. Toggle it on to start face recognition.")

    with col_status:
        st.subheader("Session status")
        snapshot = orchestrator.status_snapshot()

        state_labels = {
            SessionState.IDLE: "🔵 Waiting for a face",
            SessionState.FACE_RECOGNIZED: "🟢 Face recognized",
            SessionState.LISTENING_FOR_WAKE_WORD: "🟡 Listening for wake word",
            SessionState.DIALOG_ACTIVE: "🟣 Dialog in progress",
            SessionState.PAUSED_FOR_INTERRUPTION: "🟠 Paused — please wait",
            SessionState.SCENARIO_COMPLETE: "✅ Scenario complete",
        }
        st.metric("State", state_labels.get(snapshot.session_state, snapshot.session_state.value))
        st.write(f"**Recognized user:** {snapshot.recognized_user or '—'}")
        st.write(f"**Language:** {snapshot.language or '—'}")
        st.write(f"**Scenario / step:** {snapshot.scenario_id or '—'} / {snapshot.step_id or '—'}")

        if snapshot.last_message:
            st.info(snapshot.last_message)

        st.markdown("---")
        st.subheader("Manual controls")

        languages = orchestrator.dialog_manager.available_languages()
        lang_choice = st.selectbox(
            "Language",
            options=list(languages.keys()),
            format_func=lambda code: languages[code]["name"],
            key="dash_lang_choice",
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🎤 Listen for wake word", use_container_width=True):
                with st.spinner("Listening..."):
                    matched = orchestrator.listen_for_wake_word()
                if matched:
                    st.success("Wake word matched! Dialog started.")
                else:
                    st.warning("No wake word heard. Try again.")
                st.rerun()

        with c2:
            if st.button("🔁 Reset session", use_container_width=True):
                orchestrator.reset()
                st.rerun()

        st.caption("Or set the language and jump straight into a scenario without speaking:")
        orchestrator.dialog_manager.set_language(lang_choice)

        scenario_ids = orchestrator.dialog_manager.list_scenarios()
        scenario_choice = st.selectbox("Scenario", options=scenario_ids, key="dash_scenario_choice")
        if st.button("▶️ Start scenario", use_container_width=True):
            orchestrator.trigger_scenario(scenario_choice)
            st.rerun()

        st.markdown("---")
        st.caption(
            "While a scenario is playing, just start talking — the chatbot's "
            "voice-activity detector will pause playback and resume once "
            "you've finished."
        )


# ---------------------------------------------------------------------------
# Page: Enroll Face
# ---------------------------------------------------------------------------

def render_enroll_face():
    st.title("Enroll a face")
    st.write(
        "Register a new user so the chatbot can recognize them and play "
        "their personalized greeting. You can capture a few snapshots from "
        "the webcam (recommended — multiple angles improve accuracy) or "
        "upload a clear, front-facing photo."
    )

    face_engine = get_face_engine()
    if face_engine is None:
        st.error(
            "Face recognition isn't available. Check that dlib's model files "
            "are installed (see README), then reload this page."
        )
        return

    user_id = st.text_input("User name / ID", placeholder="e.g. abebe")

    tab_webcam, tab_upload = st.tabs(["📷 Webcam capture", "🖼️ Upload photo"])

    with tab_webcam:
        st.caption("Take 3-5 snapshots from slightly different angles for best results.")
        snapshot = st.camera_input("Capture a snapshot", key="enroll_camera")
        if snapshot is not None and user_id:
            import cv2
            import numpy as np

            file_bytes = np.asarray(bytearray(snapshot.getvalue()), dtype=np.uint8)
            frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

            if st.button("Add this snapshot to enrollment"):
                ok = face_engine.enroll(user_id, frame, append=True)
                if ok:
                    n_samples = len(face_engine.embeddings[user_id])
                    st.success(f"Snapshot added. '{user_id}' now has {n_samples} sample(s) enrolled.")
                else:
                    st.warning("No face detected in that snapshot. Try again with better lighting.")
        elif snapshot is not None and not user_id:
            st.warning("Enter a user name/ID before adding a snapshot.")

    with tab_upload:
        uploaded = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png"])
        if uploaded is not None and user_id:
            import cv2
            import numpy as np

            file_bytes = np.asarray(bytearray(uploaded.getvalue()), dtype=np.uint8)
            frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            st.image(frame, channels="BGR", caption="Uploaded photo", width=300)

            if st.button("Enroll from this photo"):
                ok = face_engine.enroll(user_id, frame, append=True)
                if ok:
                    n_samples = len(face_engine.embeddings[user_id])
                    st.success(f"Enrolled. '{user_id}' now has {n_samples} sample(s) enrolled.")
                else:
                    st.warning("No face detected in that photo. Try a clearer, front-facing image.")
        elif uploaded is not None and not user_id:
            st.warning("Enter a user name/ID before enrolling.")

    st.markdown("---")
    st.subheader("Enrolled users")
    users = face_engine.list_users()
    if not users:
        st.caption("No users enrolled yet.")
    else:
        for u in users:
            c1, c2, c3 = st.columns([3, 2, 1])
            c1.write(f"**{u}**")
            c2.write(f"{len(face_engine.embeddings[u])} sample(s)")
            if c3.button("Delete", key=f"delete_{u}"):
                face_engine.delete_user(u)
                st.rerun()


# ---------------------------------------------------------------------------
# Page: Manage Scenarios
# ---------------------------------------------------------------------------

def render_manage_scenarios():
    st.title("Manage dialog scenarios")
    st.write(
        "Dialog scenarios, languages, and audio file mappings are defined in "
        f"`{DIALOG_CONFIG_PATH.relative_to(DIALOG_CONFIG_PATH.parents[2])}`. "
        "You can review the current configuration below, or edit the raw "
        "JSON directly for advanced changes (new languages, new scenarios, "
        "branching steps)."
    )

    config = load_dialog_config()

    st.subheader("Languages")
    for code, cfg in config["languages"].items():
        with st.expander(f"{cfg['name']} ({code})"):
            st.write("**Wake words:**", ", ".join(cfg.get("wake_words", [])))
            if cfg.get("wake_words_native"):
                st.write("**Native-script wake words:**", ", ".join(cfg["wake_words_native"]))
            st.write("**Default greeting:**", cfg.get("default_greeting", "—"))

    st.subheader("Scenarios")
    for sid, scenario in config["scenarios"].items():
        if sid.startswith("_"):
            continue
        with st.expander(f"{sid} — {scenario.get('description', '')}"):
            st.write(f"**Entry step:** {scenario['entry_step']}")
            for step_id, step_cfg in scenario["steps"].items():
                st.markdown(f"**Step: `{step_id}`**")
                for lang_code in config["languages"]:
                    if lang_code in step_cfg:
                        st.write(f"- {lang_code}: `{step_cfg[lang_code]}`")
                st.write(
                    f"- interruptible: {step_cfg.get('interruptible', True)}, "
                    f"next: {step_cfg.get('next') or '(end)'}"
                )

    st.markdown("---")
    st.subheader("Advanced: raw JSON editor")
    st.caption(
        "Edit and save the full configuration. Invalid JSON or missing "
        "required fields will be rejected with an error rather than written "
        "to disk."
    )

    raw_text = DIALOG_CONFIG_PATH.read_text(encoding="utf-8")
    edited = st.text_area("dialog_config.json", value=raw_text, height=400)

    if st.button("💾 Save configuration"):
        import json

        try:
            parsed = json.loads(edited)
            required = {"languages", "scenarios", "default_scenario"}
            if not required.issubset(parsed.keys()):
                raise ValueError(f"Missing required top-level keys: {required - parsed.keys()}")
            DIALOG_CONFIG_PATH.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
            st.success("Saved. Reload the page (or restart the session) to apply changes.")
            get_orchestrator.clear()
        except Exception as exc:
            st.error(f"Could not save: {exc}")


# ---------------------------------------------------------------------------
# Page: Settings
# ---------------------------------------------------------------------------

def render_settings():
    st.title("Settings")
    st.write("These apply for the current session. Restart the app to reset to defaults.")

    st.subheader("Face recognition")
    SETTINGS.face_match_tolerance = st.slider(
        "Match tolerance (lower = stricter)", 0.3, 0.8, SETTINGS.face_match_tolerance, 0.01
    )
    SETTINGS.face_min_detections_to_confirm = st.slider(
        "Consecutive frames required to confirm a face", 1, 10, SETTINGS.face_min_detections_to_confirm
    )

    st.subheader("Speech / wake word")
    SETTINGS.whisper_model_size = st.selectbox(
        "Whisper model size", ["tiny", "base", "small", "medium"],
        index=["tiny", "base", "small", "medium"].index(SETTINGS.whisper_model_size),
    )
    st.caption("Changing the Whisper model size requires restarting the app to take effect.")
    SETTINGS.wake_word_listen_seconds = st.slider(
        "Wake-word listening duration (seconds)", 1.0, 6.0, SETTINGS.wake_word_listen_seconds, 0.5
    )

    st.subheader("Interruption handling (VAD)")
    SETTINGS.vad_aggressiveness = st.slider(
        "VAD aggressiveness (webrtcvad)", 0, 3, SETTINGS.vad_aggressiveness
    )
    SETTINGS.interruption_confirm_frames = st.slider(
        "Consecutive voiced frames required to trigger interruption", 1, 10, SETTINGS.interruption_confirm_frames
    )
    SETTINGS.audio_resume_mode = st.radio(
        "After an interruption, the chatbot should...",
        options=["restart", "resume"],
        index=["restart", "resume"].index(SETTINGS.audio_resume_mode),
        format_func=lambda v: "Restart the clip from the beginning" if v == "restart" else "Resume from where it paused",
    )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

if page == "Dashboard":
    render_dashboard()
elif page == "Enroll Face":
    render_enroll_face()
elif page == "Manage Scenarios":
    render_manage_scenarios()
elif page == "Settings":
    render_settings()
