"""Scenario management page for EthioChatbot V2's Streamlit dashboard.

Presentation-layer only: collects add/edit/delete input and displays
the scenario list, delegating all validation and persistence to
utils.scenario_engine.ScenarioEngine, per ARCHITECTURE.md's rule that
Streamlit pages must not contain business logic.

Uses its own lightweight ScenarioEngine instance (no event_bus/
state_manager) rather than the live running Application's, since
managing scenarios doesn't need the camera/Whisper pipeline running.
Edits made here take effect for the live system the next time it
reloads its scenario cache (e.g. on the next application start).
"""
from __future__ import annotations

import streamlit as st

from utils.scenario_engine import SUPPORTED_LANGUAGES, ScenarioEngine

st.set_page_config(page_title="Manage Scenarios - EthioChatbot V2", page_icon="💬")
st.title("Manage Scenarios")
st.caption(
    "Add, edit, or delete deterministic question/response scenarios. "
    "Changes are saved to audio/config/dialog_config.json immediately; "
    "the live conversation engine picks them up the next time it starts."
)

engine = ScenarioEngine()

language = st.selectbox("Language", SUPPORTED_LANGUAGES)

st.subheader("Add or Update a Scenario")
with st.form("add_scenario_form", clear_on_submit=True):
    user_text = st.text_input("User text (what the user says)")
    response_audio = st.text_input(
        "Response audio path (relative to project root)",
        placeholder=f"audio/{language}/example.wav",
    )
    submitted = st.form_submit_button("Save Scenario")

if submitted:
    try:
        engine.add_or_update_scenario(language, user_text, response_audio)
        st.success(f"Scenario saved for {language}: '{user_text}' -> {response_audio}")
    except ValueError as exc:
        st.error(str(exc))

st.divider()
st.subheader(f"{language.title()} Scenarios")

scenarios = engine.all_scenarios(language)
if not scenarios:
    st.info("No scenarios defined for this language yet.")
else:
    for scenario in scenarios:
        col_text, col_audio, col_delete = st.columns([3, 3, 1])
        col_text.write(scenario.user_text)
        col_audio.write(scenario.response_audio)
        if col_delete.button("Delete", key=f"delete_{language}_{scenario.normalized_text}"):
            engine.delete_scenario(language, scenario.user_text)
            st.rerun()
