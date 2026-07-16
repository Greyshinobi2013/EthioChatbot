"""Scenario management page (README.md "Scenario Management Requirements").

UI only: reads/writes audio/config/dialog_config.json and
config/settings.json's wake_words through utils.conversation_manager and
utils.state_manager functions -- no matching or business logic here
(CLAUDE.md "Streamlit Rule"). Every change is written to disk immediately
(load -> mutate -> save -> rerun) rather than staged in memory, so the
page always reflects what's actually on disk.
"""
from __future__ import annotations

import streamlit as st

from app import get_app_state
from utils.conversation_manager import (
    ScenarioError,
    load_scenarios_raw,
    resolve_audio_path,
    save_scenarios,
    save_uploaded_audio,
)
from utils.state_manager import load_configuration, save_configuration

state = get_app_state()

st.set_page_config(page_title="Manage Scenarios - Offline Robot", page_icon="🤖")
st.title("Manage Scenarios")

LANGUAGES = ["english", "amharic", "arabic"]
language = st.selectbox("Language", LANGUAGES, format_func=str.title)

st.subheader("Wake Words")
config = load_configuration()
wake_words = config.setdefault("wake_words", {})
language_wake_words = wake_words.setdefault(language, [])

if not language_wake_words:
    st.info("No wake words configured for this language yet.")
for i, phrase in enumerate(language_wake_words):
    col1, col2 = st.columns([5, 1])
    col1.write(phrase)
    if col2.button("🗑️ Delete", key=f"del_wake_{language}_{i}"):
        language_wake_words.pop(i)
        save_configuration(config)
        st.rerun()

with st.form(key=f"add_wake_{language}", clear_on_submit=True):
    new_wake_word = st.text_input("New wake word")
    if st.form_submit_button("➕ Add Wake Word"):
        if new_wake_word.strip():
            language_wake_words.append(new_wake_word.strip())
            save_configuration(config)
            st.rerun()
        else:
            st.error("Enter a wake word first.")

st.divider()

st.subheader("Dialogs")
try:
    scenarios = load_scenarios_raw()
except ScenarioError as exc:
    st.error(f"Could not load dialog_config.json: {exc}")
    scenarios = {}

language_scenarios = scenarios.setdefault(language, [])

if not language_scenarios:
    st.info("No dialogs configured for this language yet.")
for i, entry in enumerate(language_scenarios):
    with st.container(border=True):
        edited_text = st.text_input(
            "User says", value=entry.get("user_text", ""), key=f"text_{language}_{i}"
        )
        edited_audio = st.text_input(
            "Response audio filename", value=entry.get("response_audio", ""), key=f"audio_{language}_{i}"
        )
        audio_path = resolve_audio_path(language, edited_audio) if edited_audio.strip() else None
        if audio_path is not None and audio_path.exists():
            st.audio(str(audio_path))
        elif edited_audio.strip():
            st.warning(f"Audio file not found: {audio_path}")

        col1, col2 = st.columns(2)
        if col1.button("💾 Update", key=f"upd_{language}_{i}"):
            language_scenarios[i] = {
                "user_text": edited_text.strip(),
                "response_audio": edited_audio.strip(),
            }
            save_scenarios(scenarios)
            st.rerun()
        if col2.button("🗑️ Delete", key=f"del_dialog_{language}_{i}"):
            language_scenarios.pop(i)
            save_scenarios(scenarios)
            st.rerun()

st.markdown("**Add New Dialog**")
with st.form(key=f"add_dialog_{language}", clear_on_submit=True):
    new_user_text = st.text_input("User says (e.g. 'what is your name')")
    new_response_audio = st.text_input("Response audio filename (e.g. name.wav)")
    if st.form_submit_button("➕ Add Dialog"):
        if new_user_text.strip() and new_response_audio.strip():
            language_scenarios.append({
                "user_text": new_user_text.strip(),
                "response_audio": new_response_audio.strip(),
            })
            save_scenarios(scenarios)
            st.rerun()
        else:
            st.error("Both fields are required.")

st.divider()

st.subheader("Upload / Replace Response Audio")
st.caption(
    "Uploading a file with the same name as an existing dialog's response "
    "audio replaces it in place."
)
uploaded_audio = st.file_uploader("WAV or MP3 file", type=["wav", "mp3"], key=f"upload_{language}")
if uploaded_audio is not None and st.button("💾 Save Audio File", key=f"save_audio_{language}"):
    path = save_uploaded_audio(language, uploaded_audio.name, uploaded_audio.getvalue())
    st.success(f"Saved to {path}. Reference it as '{uploaded_audio.name}' in a dialog above.")
