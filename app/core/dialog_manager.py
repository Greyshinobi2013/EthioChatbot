"""
Dialog Manager.

Owns the "what plays next" logic: given the active scenario, the
current step, and the active language, resolve the audio file path.
This is intentionally pure/state-machine-like and has no knowledge of
audio playback, face recognition, or speech -- those are wired
together in core.orchestrator. Keeping this module dumb makes it easy
to unit test and easy for a non-engineer content author to extend by
editing dialog_config.json alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.core.config import load_dialog_config, resolve_audio_path, get_logger

logger = get_logger(__name__)


@dataclass
class DialogState:
    user_id: Optional[str] = None
    language: Optional[str] = None
    scenario_id: Optional[str] = None
    step_id: Optional[str] = None
    history: list[str] = field(default_factory=list)  # step ids visited, for debugging/UI


class DialogManager:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or load_dialog_config()
        self.state = DialogState()

    # -- language / session setup --------------------------------------------

    def available_languages(self) -> dict:
        return self.config["languages"]

    def set_language(self, language_code: str) -> None:
        if language_code not in self.config["languages"]:
            raise ValueError(f"Unknown language code: {language_code}")
        self.state.language = language_code

    def set_user(self, user_id: Optional[str]) -> None:
        self.state.user_id = user_id

    # -- greeting resolution --------------------------------------------------

    def get_greeting_audio(self, user_id: Optional[str] = None, language: Optional[str] = None) -> Optional[str]:
        """Resolve the greeting clip for a recognized user in the given
        language, falling back to the 'default' greeting if this
        specific user has no custom greeting configured."""
        user_id = user_id or self.state.user_id or "default"
        language = language or self.state.language

        if language is None:
            logger.warning("get_greeting_audio called with no active language")
            return None

        greetings = self.config.get("user_greetings", {})
        user_entry = greetings.get(user_id) or greetings.get("default", {})
        relative_path = user_entry.get(language)

        if relative_path is None:
            # last-resort fallback: the language's own default_greeting
            relative_path = self.config["languages"][language].get("default_greeting")

        return relative_path

    # -- scenario navigation --------------------------------------------------

    def start_scenario(self, scenario_id: Optional[str] = None) -> str:
        """Begin (or restart) a scenario, returning the relative audio
        path for its entry step."""
        scenario_id = scenario_id or self.config["default_scenario"]
        if scenario_id not in self.config["scenarios"]:
            raise ValueError(f"Unknown scenario_id: {scenario_id}")

        scenario = self.config["scenarios"][scenario_id]
        entry_step = scenario["entry_step"]

        self.state.scenario_id = scenario_id
        self.state.step_id = entry_step
        self.state.history = [entry_step]

        return self._audio_path_for_current_step()

    def advance(self) -> Optional[str]:
        """Move to the 'next' step of the current scenario step and
        return its audio path, or None if the scenario has ended."""
        if self.state.scenario_id is None or self.state.step_id is None:
            raise RuntimeError("No active scenario; call start_scenario() first.")

        scenario = self.config["scenarios"][self.state.scenario_id]
        current_step_cfg = scenario["steps"][self.state.step_id]
        next_step_id = current_step_cfg.get("next")

        if next_step_id is None:
            logger.info("Scenario '%s' reached its end.", self.state.scenario_id)
            self.state.step_id = None
            return None

        self.state.step_id = next_step_id
        self.state.history.append(next_step_id)
        return self._audio_path_for_current_step()

    def jump_to_scenario(self, scenario_id: str) -> str:
        """Used e.g. when a recognized intent/keyword should branch the
        conversation into a different scenario (FAQ, goodbye, etc.)."""
        return self.start_scenario(scenario_id)

    def current_step_is_interruptible(self) -> bool:
        if self.state.scenario_id is None or self.state.step_id is None:
            return True
        scenario = self.config["scenarios"][self.state.scenario_id]
        step_cfg = scenario["steps"][self.state.step_id]
        return bool(step_cfg.get("interruptible", True))

    def current_audio_absolute_path(self):
        relative = self._audio_path_for_current_step()
        return resolve_audio_path(relative) if relative else None

    # -- internals --------------------------------------------------------------

    def _audio_path_for_current_step(self) -> Optional[str]:
        if self.state.scenario_id is None or self.state.step_id is None:
            return None
        if self.state.language is None:
            raise RuntimeError("No active language set; call set_language() first.")

        scenario = self.config["scenarios"][self.state.scenario_id]
        step_cfg = scenario["steps"][self.state.step_id]
        relative_path = step_cfg.get(self.state.language)

        if relative_path is None:
            logger.warning(
                "Step '%s' in scenario '%s' has no audio for language '%s'",
                self.state.step_id, self.state.scenario_id, self.state.language,
            )
        return relative_path

    def list_scenarios(self) -> list[str]:
        return sorted(self.config["scenarios"].keys())

    def scenario_description(self, scenario_id: str) -> str:
        return self.config["scenarios"].get(scenario_id, {}).get("description", "")
