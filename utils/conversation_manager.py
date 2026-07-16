"""Conversation orchestration.

Milestone 2 added the automatic greeting workflow (FACE_DETECTED ->
FACE_RECOGNIZED -> GREETING -> WAITING_FOR_WAKE_WORD). Milestone 3 added
wake-word activation and language selection (WAITING_FOR_WAKE_WORD ->
LANGUAGE_SELECTION -> CONVERSATION_ACTIVE, per STATE_MACHINE.md). Milestone
4 added the scenario engine (ARCHITECTURE.md "Scenario Service": load
scenarios, normalize text, match, locate response audio). Milestone 6
wires live transcriptions from CONVERSATION_ACTIVE speech into that engine
and adds timeout handling (CONVERSATION_ACTIVE -> TIMEOUT ->
RETURN_TO_IDLE -> IDLE).
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import TypedDict

from utils.event_bus import publish, subscribe
from utils.logger import get_logger
from utils.playback import play_audio
from utils.state_manager import AppState
from utils.whisper_utils import normalize_text

logger = get_logger("conversation_manager")

AUDIO_ROOT = Path("audio")
GREETING_LANGUAGE_DEFAULT = "english"
DIALOG_CONFIG_PATH = Path("audio/config/dialog_config.json")
FALLBACK_AUDIO_NAME = "unknown_question.wav"
TIMEOUT_POLL_SECONDS = 0.5


class Scenario(TypedDict):
    user_text: str
    response_audio: str


class ScenarioError(RuntimeError):
    """Raised when the dialog configuration is missing or malformed."""


# Common function words excluded from keyword matching so two questions
# that only share words like "what"/"is"/"your" don't falsely match
# (e.g. "what is the weather" must not match "what is your name"). This is
# a fixed word list, not semantic search or embeddings, so it stays within
# SCENARIOS.md's deterministic-matching requirement. Languages without an
# entry here fall back to matching on all words unfiltered.
_STOPWORDS: dict[str, set[str]] = {
    "english": {
        "a", "an", "the",
        "is", "are", "was", "were", "am", "be", "been", "being",
        "what", "who", "where", "when", "how", "why", "which",
        "do", "does", "did", "doing",
        "i", "you", "he", "she", "it", "we", "they",
        "me", "him", "her", "us", "them",
        "my", "your", "his", "its", "our", "their",
        "to", "of", "in", "on", "at", "for", "with",
        "please", "hey", "hi", "hello", "tell", "there",
        "can", "could", "would", "will", "shall", "should",
    },
}


def _content_words(text: str, language: str) -> set[str]:
    """Normalized words with common function words removed for keyword matching.

    Falls back to the full word set if stripping stopwords would leave
    nothing (e.g. the text IS just "hello").
    """
    words = set(normalize_text(text).split())
    stopwords = _STOPWORDS.get(language, set())
    content = words - stopwords
    return content or words


def _greeting_audio_path(language: str = GREETING_LANGUAGE_DEFAULT) -> Path:
    return AUDIO_ROOT / language / "greeting.wav"


def handle_face_detected(event: dict, state: AppState) -> None:
    if state.current_state == "IDLE":
        state.set_state("FACE_DETECTED")


def handle_face_recognized(event: dict, state: AppState) -> None:
    # FACE_RECOGNIZED is only a valid transition from FACE_DETECTED
    # (STATE_MACHINE.md). Without this guard, ordinary camera flicker
    # (brief FACE_LOST/FACE_DETECTED cycles while already greeted) replays
    # the full greeting workflow every time, which also starves later
    # states of camera/event-bus attention.
    if state.current_state != "FACE_DETECTED":
        return

    user_id = event.get("user_id")

    state.set_state("FACE_RECOGNIZED")
    state.set_state("GREETING")
    publish("GREETING_STARTED", user_id=user_id)

    greeting_path = _greeting_audio_path()
    if greeting_path.exists():
        try:
            play_audio(greeting_path)
        except Exception:
            logger.exception("Failed to play greeting audio for '%s'", user_id)
    else:
        logger.error("Greeting audio not found: %s", greeting_path)

    publish("GREETING_FINISHED", user_id=user_id)
    state.set_state("WAITING_FOR_WAKE_WORD")


def handle_wake_word_detected(event: dict, state: AppState) -> None:
    if state.current_state != "WAITING_FOR_WAKE_WORD":
        logger.warning(
            "WAKE_WORD_DETECTED received outside WAITING_FOR_WAKE_WORD "
            "(current=%s); ignoring", state.current_state,
        )
        return

    language = event.get("language")

    state.set_state("LANGUAGE_SELECTION")
    state.set_status("current_language", language)
    publish("LANGUAGE_SELECTED", language=language)
    logger.info("Language selected: %s (from wake word '%s')", language, event.get("phrase"))

    state.set_state("CONVERSATION_ACTIVE")


def handle_transcription_ready(event: dict, state: AppState) -> None:
    """React to a transcribed question during CONVERSATION_ACTIVE: match a
    scenario (or fall back) and play the response.

    Silence (empty transcription) is not an error and must not trigger the
    fallback "I don't understand" audio -- it just means nothing was said
    in that chunk.
    """
    if state.current_state != "CONVERSATION_ACTIVE":
        return

    text = event.get("text", "")
    if not text.strip():
        return

    language = state.current_language or GREETING_LANGUAGE_DEFAULT
    scenarios = load_scenarios()
    match = match_scenario(text, language, scenarios)

    if match is not None:
        publish("SCENARIO_MATCHED", user_text=text, response_audio=match["response_audio"])
        response_path = Path(match["response_audio"])
    else:
        publish("SCENARIO_NOT_FOUND", user_text=text)
        response_path = AUDIO_ROOT / language / FALLBACK_AUDIO_NAME

    play_response(response_path, state)


def play_response(path: Path, state: AppState) -> None:
    """Play a response audio file with live interruption support.

    Blocks until the response has fully finished, including any
    pause/notify/resume cycles handled concurrently by vad_handler's
    background thread (STATE_MACHINE.md "Conversation Workflow":
    CONVERSATION_ACTIVE -> PLAYING_AUDIO -> CONVERSATION_ACTIVE). Used for
    both scenario responses (wired in Milestone 6) and the automatic
    greeting's audio system counterpart.
    """
    path = Path(path)
    state.set_state("PLAYING_AUDIO")
    state.set_status("playback_status", "PLAYING")
    publish("PLAYBACK_STARTED", path=str(path))

    if path.exists():
        try:
            play_audio(path, wait=True)
        except Exception:
            logger.exception("Playback failed for %s", path)
    else:
        logger.error("Response audio not found: %s", path)

    state.set_status("playback_status", "IDLE")
    publish("PLAYBACK_FINISHED", path=str(path))

    if state.current_state == "PLAYING_AUDIO":
        state.set_state("CONVERSATION_ACTIVE")


def resolve_audio_path(language: str, response_audio: str) -> Path:
    """Resolve a scenario's response_audio to a real file path.

    Accepts either a full relative path ("audio/english/name.wav", the
    format already used in audio/config/dialog_config.json) or a bare
    filename ("name.wav", per README.md's simplified example), resolving
    the latter against audio/<language>/. A multi-part path is treated as
    already-qualified even when missing, so a genuinely missing file is
    reported at its real (single) location instead of being doubled up
    under audio/<language>/ again.
    """
    candidate = Path(response_audio)
    if candidate.exists() or candidate.is_absolute() or len(candidate.parts) > 1:
        return candidate
    return AUDIO_ROOT / language / response_audio


def load_scenarios(path: Path = DIALOG_CONFIG_PATH) -> dict[str, list[Scenario]]:
    """Load and validate the scenario database (SCENARIOS.md "Scenario Validation").

    Entries missing user_text/response_audio, or whose audio file does not
    exist on disk, are dropped and logged rather than raising -- one bad
    entry should not break scenario matching for every other entry.
    """
    if not path.exists():
        raise ScenarioError(f"Dialog configuration not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScenarioError(f"Dialog configuration is not valid JSON: {path}") from exc

    validated: dict[str, list[Scenario]] = {}
    for language, entries in data.items():
        valid_entries: list[Scenario] = []
        for entry in entries:
            user_text = entry.get("user_text")
            response_audio = entry.get("response_audio")
            if not user_text or not response_audio:
                logger.warning("Skipping invalid scenario entry in '%s': %r", language, entry)
                continue

            audio_path = resolve_audio_path(language, response_audio)
            if not audio_path.exists():
                logger.warning(
                    "Scenario audio file missing for '%s' (%r): %s",
                    language, user_text, audio_path,
                )
                continue

            valid_entries.append({"user_text": user_text, "response_audio": str(audio_path)})

        validated[language] = valid_entries
        logger.info("Loaded %d valid scenario(s) for language '%s'", len(valid_entries), language)

    return validated


def load_scenarios_raw(path: Path = DIALOG_CONFIG_PATH) -> dict[str, list[Scenario]]:
    """Load the scenario database exactly as stored, with no filtering.

    load_scenarios() silently drops invalid/broken entries for the runtime
    matching engine; the Scenario Management page needs to show and let an
    admin fix those entries, so it uses this instead.
    """
    if not path.exists():
        raise ScenarioError(f"Dialog configuration not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScenarioError(f"Dialog configuration is not valid JSON: {path}") from exc


def save_scenarios(scenarios: dict[str, list[Scenario]], path: Path = DIALOG_CONFIG_PATH) -> None:
    """Persist the scenario database back to disk (Scenario Management page)."""
    path.write_text(json.dumps(scenarios, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Scenario database saved to %s", path.resolve())


def save_uploaded_audio(language: str, filename: str, data: bytes) -> Path:
    """Save an uploaded audio file under audio/<language>/ and return its path."""
    target_dir = AUDIO_ROOT / language
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename
    target_path.write_bytes(data)
    logger.info("Uploaded audio saved to %s", target_path)
    return target_path


def match_scenario(
    text: str, language: str, scenarios: dict[str, list[Scenario]]
) -> Scenario | None:
    """Find the best-matching scenario for text within language only.

    Priority (SCENARIOS.md "Matching Strategy"): exact normalized match,
    then keyword (word-overlap) match, highest score wins. Deterministic
    only -- no semantic search, no embeddings, no LLM. Scenarios are
    searched only within the active language, never across languages.
    """
    normalized_input = normalize_text(text)
    language_scenarios = scenarios.get(language, [])
    if not normalized_input or not language_scenarios:
        return None

    for entry in language_scenarios:
        if normalize_text(entry["user_text"]) == normalized_input:
            return entry

    input_content = _content_words(text, language)
    best_entry: Scenario | None = None
    best_score = 0
    for entry in language_scenarios:
        entry_content = _content_words(entry["user_text"], language)
        overlap = len(input_content & entry_content)
        if overlap > best_score:
            best_score = overlap
            best_entry = entry

    return best_entry


def resolve_response_audio(
    text: str, language: str, scenarios: dict[str, list[Scenario]]
) -> Path:
    """Return the audio file to play for text: matched scenario, or the
    per-language fallback (SCENARIOS.md "Fallback Response") if no
    scenario matches.
    """
    match = match_scenario(text, language, scenarios)
    if match is not None:
        return Path(match["response_audio"])

    logger.info("No scenario matched %r in language '%s'; using fallback", text, language)
    return AUDIO_ROOT / language / FALLBACK_AUDIO_NAME


def _handle_timeout(state: AppState) -> None:
    """Run the timeout cascade: CONVERSATION_ACTIVE -> TIMEOUT ->
    RETURN_TO_IDLE -> IDLE (STATE_MACHINE.md "Timeout Workflow").

    Clears recognized_user/current_language so the next visitor starts
    from a genuinely clean IDLE state rather than carrying over the
    previous conversation's identity/language.
    """
    logger.info("Conversation timeout reached (%ss of inactivity)", state.config["conversation_timeout"])
    publish("TIMEOUT_OCCURRED")
    state.set_state("TIMEOUT")

    state.set_state("RETURN_TO_IDLE")
    publish("RETURN_TO_IDLE")
    state.set_status("current_language", None)
    state.set_status("recognized_user", None)

    state.set_state("IDLE")


def monitor_timeout(state: AppState, stop_event: threading.Event) -> None:
    """Background thread target: watch how long CONVERSATION_ACTIVE has
    been continuously active and trigger the timeout cascade once it
    exceeds config["conversation_timeout"] seconds.

    The clock resets naturally every time CONVERSATION_ACTIVE is freshly
    (re-)entered -- including right after a response finishes playing
    (play_response() returns to CONVERSATION_ACTIVE) -- so the timeout
    measures "time since the last question was answered", not total
    conversation length.
    """
    conversation_active_since: float | None = None

    while not stop_event.is_set():
        if state.current_state != "CONVERSATION_ACTIVE":
            conversation_active_since = None
            time.sleep(TIMEOUT_POLL_SECONDS)
            continue

        if conversation_active_since is None:
            conversation_active_since = time.monotonic()

        elapsed = time.monotonic() - conversation_active_since
        if elapsed >= state.config["conversation_timeout"]:
            _handle_timeout(state)
            conversation_active_since = None

        time.sleep(TIMEOUT_POLL_SECONDS)


def register_handlers(state: AppState) -> None:
    """Wire conversation-manager event handlers to the shared event bus."""
    subscribe("FACE_DETECTED", lambda event: handle_face_detected(event, state))
    subscribe("FACE_RECOGNIZED", lambda event: handle_face_recognized(event, state))
    subscribe("WAKE_WORD_DETECTED", lambda event: handle_wake_word_detected(event, state))
    subscribe("TRANSCRIPTION_READY", lambda event: handle_transcription_ready(event, state))
    logger.info("Conversation manager handlers registered")
