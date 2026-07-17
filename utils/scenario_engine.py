"""Deterministic scenario matching engine for EthioChatbot V2.

Loads audio/config/dialog_config.json once, builds per-language lookup
caches, and matches normalized user speech against them, per
SCENARIOS.md's Matching Strategy: exact match first, then keyword
match, then a fallback response. Matching is plain dictionary lookups
and substring checks only -- no LLMs, embeddings, vector search, or
any other AI-reasoning-based matching are used, per SCENARIOS.md's
Unsupported Matching Methods list.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from utils.event_bus import Event, EventBus
from utils.logger import get_logger
from utils.state_manager import StateManager

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIALOG_CONFIG_PATH = PROJECT_ROOT / "audio" / "config" / "dialog_config.json"

SUPPORTED_LANGUAGES = ("english", "amharic", "arabic")

DEFAULT_FALLBACK_AUDIO: Dict[str, Path] = {
    "english": PROJECT_ROOT / "audio" / "english" / "unknown_question.wav",
    "amharic": PROJECT_ROOT / "audio" / "amharic" / "unknown_question.wav",
    "arabic": PROJECT_ROOT / "audio" / "arabic" / "unknown_question.wav",
}


def normalize_text(text: str) -> str:
    """Normalize text for scenario matching, per SCENARIOS.md's Text Normalization rules.

    Steps: lowercase, strip Unicode punctuation (script-agnostic, so
    Amharic/Arabic punctuation is handled correctly, not just ASCII),
    collapse repeated whitespace, trim.
    """
    lowered = text.lower()
    no_punctuation = "".join(ch for ch in lowered if not unicodedata.category(ch).startswith("P"))
    collapsed = re.sub(r"\s+", " ", no_punctuation)
    return collapsed.strip()


@dataclass(frozen=True)
class Scenario:
    """A single deterministic question/response pair.

    Attributes:
        user_text: The original scenario phrase, as written in
            dialog_config.json.
        normalized_text: user_text after normalize_text().
        response_audio: Path to the response WAV, relative to the
            project root (e.g. "audio/english/name.wav").
    """

    user_text: str
    normalized_text: str
    response_audio: str


@dataclass(frozen=True)
class ScenarioMatch:
    """Result of a successful scenario match.

    Attributes:
        response_audio: Relative path to the WAV to play.
        match_type: "exact" or "keyword".
        scenario: The matched Scenario record.
    """

    response_audio: str
    match_type: str
    scenario: Scenario


class ScenarioEngine:
    """Loads, caches, and matches deterministic conversation scenarios.

    Per README's Raspberry Pi optimization guidance, dialog_config.json
    is read once (at construction, or via reload via load_scenarios())
    and converted into per-language lookup dictionaries --
    english_lookup, amharic_lookup, arabic_lookup -- that are reused
    for every match. No JSON is re-read, and no embeddings or search
    index of any kind is built.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        state_manager: Optional[StateManager] = None,
        dialog_config_path: Path = DEFAULT_DIALOG_CONFIG_PATH,
        fallback_audio: Optional[Dict[str, Path]] = None,
    ) -> None:
        """Args:
            event_bus: Bus to react to TRANSCRIPTION_READY on and
                publish SCENARIO_MATCHED/SCENARIO_NOT_FOUND/
                FALLBACK_SCENARIO_SELECTED to. Optional so match() can
                be used as a pure function without full app wiring.
            state_manager: Shared state to read current_language from
                when reacting to TRANSCRIPTION_READY. Optional for the
                same reason as event_bus.
            dialog_config_path: Path to dialog_config.json.
            fallback_audio: Per-language unknown_question.wav paths;
                defaults to DEFAULT_FALLBACK_AUDIO.
        """
        self._bus = event_bus
        self._state = state_manager
        self._dialog_config_path = Path(dialog_config_path)
        self._fallback_audio: Dict[str, Path] = {
            language: Path(path) for language, path in (fallback_audio or DEFAULT_FALLBACK_AUDIO).items()
        }

        self.english_lookup: Dict[str, Scenario] = {}
        self.amharic_lookup: Dict[str, Scenario] = {}
        self.arabic_lookup: Dict[str, Scenario] = {}
        self._lookups: Dict[str, Dict[str, Scenario]] = {
            "english": self.english_lookup,
            "amharic": self.amharic_lookup,
            "arabic": self.arabic_lookup,
        }
        self._scenario_lists: Dict[str, List[Scenario]] = {language: [] for language in SUPPORTED_LANGUAGES}

        self.load_scenarios()

        if self._bus is not None:
            self._bus.subscribe("TRANSCRIPTION_READY", self._on_transcription_ready)

    def load_scenarios(self) -> None:
        """Load dialog_config.json and rebuild the per-language lookup caches.

        Invalid entries (missing user_text/response_audio, a
        response_audio file that doesn't exist on disk, or text that
        normalizes to nothing) are logged and skipped rather than
        failing the whole load, per SCENARIOS.md's Scenario Validation
        Rules.
        """
        if not self._dialog_config_path.exists():
            logger.error("Dialog config not found: %s", self._dialog_config_path)
            raw_config: dict = {}
        else:
            with self._dialog_config_path.open("r", encoding="utf-8") as handle:
                raw_config = json.load(handle)

        for language in SUPPORTED_LANGUAGES:
            lookup = self._lookups[language]
            lookup.clear()
            scenario_list: List[Scenario] = []

            for entry in raw_config.get(language, []):
                scenario = self._validate_entry(language, entry)
                if scenario is None:
                    continue
                if scenario.normalized_text in lookup:
                    logger.warning(
                        "Duplicate %s scenario text '%s'; keeping the later entry",
                        language,
                        scenario.normalized_text,
                    )
                lookup[scenario.normalized_text] = scenario
                scenario_list.append(scenario)

            self._scenario_lists[language] = scenario_list
            logger.info("Loaded %d %s scenario(s)", len(scenario_list), language)

    def _validate_entry(self, language: str, entry: dict) -> Optional[Scenario]:
        """Validate one raw dialog_config.json entry, returning a Scenario or None."""
        user_text = entry.get("user_text")
        response_audio = entry.get("response_audio")

        if not user_text or not response_audio:
            logger.warning(
                "Invalid %s scenario entry (missing user_text/response_audio): %s", language, entry
            )
            return None

        audio_path = PROJECT_ROOT / response_audio
        if not audio_path.exists():
            logger.warning(
                "Invalid %s scenario entry (audio file not found: %s): %s", language, audio_path, entry
            )
            return None

        normalized = normalize_text(user_text)
        if not normalized:
            logger.warning("Invalid %s scenario entry (user_text is empty after normalization): %s", language, entry)
            return None

        return Scenario(user_text=user_text, normalized_text=normalized, response_audio=response_audio)

    def match(self, text: str, language: str) -> Optional[ScenarioMatch]:
        """Match user speech against the given language's scenarios.

        Priority order, per SCENARIOS.md: exact match, then keyword
        match (the scenario's full normalized phrase appears as a
        contiguous substring of the normalized input). Only the
        specified language's scenarios are searched, per SCENARIOS.md's
        Multi-Language Matching rule.

        Args:
            text: Raw (not yet normalized) transcribed user speech.
            language: One of SUPPORTED_LANGUAGES.

        Returns:
            A ScenarioMatch, or None if nothing matched (caller should
            use fallback_audio_for(language)).

        Raises:
            ValueError: if language is not supported.
        """
        if language not in self._lookups:
            raise ValueError(f"Unsupported language: {language}")

        normalized = normalize_text(text)
        if not normalized:
            return None

        lookup = self._lookups[language]
        exact = lookup.get(normalized)
        if exact is not None:
            return ScenarioMatch(response_audio=exact.response_audio, match_type="exact", scenario=exact)

        for scenario in self._scenario_lists[language]:
            if scenario.normalized_text in normalized:
                return ScenarioMatch(response_audio=scenario.response_audio, match_type="keyword", scenario=scenario)

        return None

    def fallback_audio_for(self, language: str) -> Path:
        """Return the unknown_question.wav path for language.

        Raises:
            ValueError: if language is not supported.
        """
        if language not in self._fallback_audio:
            raise ValueError(f"Unsupported language: {language}")
        return self._fallback_audio[language]

    def _on_transcription_ready(self, event: Event) -> None:
        """Bus callback: match TRANSCRIPTION_READY's text and publish the result."""
        if self._state is None:
            logger.warning("Received TRANSCRIPTION_READY but no state_manager was configured; ignoring")
            return

        language = self._state.current_language
        if language is None:
            logger.warning("Received TRANSCRIPTION_READY with no current_language set; ignoring")
            return

        text = event.payload.get("text", "")
        result = self.match(text, language)

        if result is not None:
            logger.info("SCENARIO_MATCHED (%s): '%s' -> %s", result.match_type, text, result.response_audio)
            self._bus.publish("SCENARIO_MATCHED", {"audio_file": result.response_audio})
            return

        logger.info("SCENARIO_NOT_FOUND for '%s' (language=%s)", text, language)
        self._bus.publish("SCENARIO_NOT_FOUND", {})

        fallback_path = self.fallback_audio_for(language)
        fallback_relative = str(fallback_path.relative_to(PROJECT_ROOT))
        self._bus.publish("FALLBACK_SCENARIO_SELECTED", {"audio_file": fallback_relative})
