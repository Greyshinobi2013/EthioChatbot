"""Whisper speech recognition and wake-word detection for EthioChatbot V2.

Loads OpenAI Whisper's "base" model once and reuses it, per
ARCHITECTURE.md's Whisper Service responsibilities: wake word
detection, speech transcription, language recognition. The base model
supports English, Amharic, and Arabic while remaining efficient
enough for Raspberry Pi 4.

Per README.md's Wake Word System, there is no separate language
selection stage: whichever language's wake-word list a transcribed
utterance matches directly becomes current_language for the session
(WAKE_WORD_DETECTED's language payload), consistent with the Language
Selection Rule's first priority tier (Wake Word Language).
"""
from __future__ import annotations

import re
import threading
import unicodedata
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
import whisper

from utils.event_bus import EventBus
from utils.logger import get_logger
from utils.state_manager import StateManager

logger = get_logger(__name__)

DEFAULT_MODEL_SIZE = "base"

# Whisper's target sample rate; audio fed to transcribe()/detect_wake_word()
# must be mono float32 PCM in [-1, 1] at this rate.
WHISPER_SAMPLE_RATE = 16000

# Whisper language codes -> EthioChatbot's internal language names, and the reverse.
_WHISPER_LANGUAGE_TO_NAME: Dict[str, str] = {
    "en": "english",
    "am": "amharic",
    "ar": "arabic",
}
_NAME_TO_WHISPER_LANGUAGE: Dict[str, str] = {name: code for code, name in _WHISPER_LANGUAGE_TO_NAME.items()}

WAKE_WORDS: Dict[str, Tuple[str, ...]] = {
    "english": ("hello robot", "hey robot", "computer"),
    "amharic": ("ሰላም ሮቦት", "ሄይ ሮቦት"),
    "arabic": ("مرحبا روبوت", "أهلا روبوت"),
}

SUPPORTED_LANGUAGES = tuple(WAKE_WORDS.keys())


def normalize_text(text: str) -> str:
    """Normalize transcribed text for wake-word/scenario matching.

    Steps, per SCENARIOS.md's Text Normalization rules: lowercase,
    strip Unicode punctuation (script-agnostic, so Amharic/Arabic
    punctuation is handled correctly, not just ASCII), collapse
    repeated whitespace, trim.
    """
    lowered = text.lower()
    no_punctuation = "".join(ch for ch in lowered if not unicodedata.category(ch).startswith("P"))
    collapsed = re.sub(r"\s+", " ", no_punctuation)
    return collapsed.strip()


@dataclass(frozen=True)
class WakeWordMatch:
    """A successfully detected wake word.

    Attributes:
        language: One of SUPPORTED_LANGUAGES; becomes current_language.
        matched_phrase: The specific wake-word phrase that matched.
        transcribed_text: The normalized Whisper transcription.
    """

    language: str
    matched_phrase: str
    transcribed_text: str


class _WhisperModel:
    """Lazily-loaded, process-wide singleton for the Whisper model.

    Per ARCHITECTURE.md, Whisper must be "Loaded once, Reused
    continuously" -- expensive to load, so every WhisperService
    instance in this process shares one model.
    """

    _model = None
    _model_size: Optional[str] = None
    _lock = threading.Lock()

    @classmethod
    def get(cls, model_size: str = DEFAULT_MODEL_SIZE):
        """Return the shared Whisper model, loading it on first use."""
        with cls._lock:
            if cls._model is None:
                logger.info("Loading Whisper model: %s", model_size)
                cls._model = whisper.load_model(model_size)
                cls._model_size = model_size
            elif cls._model_size != model_size:
                logger.warning(
                    "Whisper model already loaded as '%s'; ignoring request for '%s' "
                    "(only one cached model is held per process)",
                    cls._model_size,
                    model_size,
                )
            return cls._model


class WhisperService:
    """Wake-word detection and speech transcription using OpenAI Whisper.

    Implements app.py's Service protocol (name, start, stop). Unlike
    CameraService, this service owns no hardware and no capture
    thread -- utils/audio_service.py (a later milestone) is
    responsible for continuous microphone capture and will feed
    audio buffers to process_audio(). start()/stop() here are
    lightweight lifecycle hooks since the model is loaded eagerly at
    construction, matching Whisper's "loaded once" requirement.
    """

    name = "whisper_service"

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        state_manager: Optional[StateManager] = None,
        model_size: str = DEFAULT_MODEL_SIZE,
    ) -> None:
        """Args:
            event_bus: Bus to publish WAKE_WORD_DETECTED/WAKE_WORD_REJECTED
                on. Optional so detect_wake_word()/transcribe() can be
                used as pure functions without full app wiring.
            state_manager: Shared state to set current_language on
                when a wake word is detected. Optional for the same
                reason as event_bus.
            model_size: Whisper model size to load (README recommends
                "base" for Raspberry Pi 4).
        """
        self._bus = event_bus
        self._state = state_manager
        self._model_size = model_size
        self._model = _WhisperModel.get(model_size)

    def start(self) -> None:
        """Lifecycle hook for ServiceRegistry compatibility; the model is already loaded."""
        logger.info("Whisper service ready (model=%s)", self._model_size)

    def stop(self) -> None:
        """Lifecycle hook for ServiceRegistry compatibility; no resources to release."""
        logger.info("Whisper service stopped")

    def transcribe(self, audio: np.ndarray, language: Optional[str] = None) -> Tuple[str, str]:
        """Transcribe an audio buffer.

        Args:
            audio: Mono float32 PCM samples at WHISPER_SAMPLE_RATE
                (16kHz), normalized to [-1, 1], per Whisper's expected
                input format.
            language: Force a specific Whisper language code (e.g.
                "en"); None lets Whisper auto-detect from the audio.

        Returns:
            (whisper_detected_language_code, raw_transcribed_text)
        """
        result = self._model.transcribe(audio, language=language, fp16=False)
        return result.get("language", ""), result.get("text", "")

    def detect_wake_word(self, audio: np.ndarray) -> Optional[WakeWordMatch]:
        """Transcribe audio and check it against the wake-word catalog.

        Uses a single Whisper call with language auto-detection rather
        than re-transcribing once per supported language, to keep
        this affordable on Raspberry Pi 4. The transcription is then
        checked against all three languages' wake-word lists (cheap
        string comparisons), so an occasional language
        auto-misdetection by Whisper does not prevent a match.

        Args:
            audio: Mono float32 PCM samples at 16kHz.

        Returns:
            A WakeWordMatch if a wake word was recognized, else None.
        """
        whisper_language_code, raw_text = self.transcribe(audio, language=None)
        normalized = normalize_text(raw_text)

        if not normalized:
            logger.debug("Empty transcription; no wake word possible")
            return None

        for candidate_language, phrases in WAKE_WORDS.items():
            for phrase in phrases:
                normalized_phrase = normalize_text(phrase)
                if normalized_phrase == normalized or normalized_phrase in normalized:
                    logger.info(
                        "Wake word matched: language=%s phrase='%s' whisper_detected='%s' transcription='%s'",
                        candidate_language,
                        phrase,
                        whisper_language_code,
                        normalized,
                    )
                    return WakeWordMatch(
                        language=candidate_language,
                        matched_phrase=phrase,
                        transcribed_text=normalized,
                    )

        logger.debug(
            "No wake word matched (whisper_detected_language=%s transcription='%s')",
            whisper_language_code,
            normalized,
        )
        return None

    def process_audio(self, audio: np.ndarray) -> Optional[WakeWordMatch]:
        """Run wake-word detection on an audio buffer and drive the FSM.

        On a match: sets state_manager.current_language and publishes
        WAKE_WORD_DETECTED (which the Milestone 2 FSM's own
        subscription advances WAITING_FOR_WAKE_WORD -> CONVERSATION_ACTIVE
        with). On no match: publishes WAKE_WORD_REJECTED.

        Requires this WhisperService to have been constructed with an
        event_bus and state_manager.

        Args:
            audio: Mono float32 PCM samples at 16kHz.

        Returns:
            The WakeWordMatch if one was found, else None.

        Raises:
            RuntimeError: if this instance was constructed without an
                event_bus/state_manager.
        """
        if self._bus is None or self._state is None:
            raise RuntimeError(
                "process_audio() requires WhisperService to be constructed with an event_bus and state_manager"
            )

        match = self.detect_wake_word(audio)
        if match is not None:
            self._state.set_current_language(match.language)
            self._bus.publish("WAKE_WORD_DETECTED", {"language": match.language})
        else:
            self._bus.publish("WAKE_WORD_REJECTED", {})
        return match

    def transcribe_and_publish(self, audio: np.ndarray) -> str:
        """Transcribe a captured utterance and publish the result.

        Used during CONVERSATION_ACTIVE (Milestone 13's audio service
        hands it a captured question) to transcribe using the
        established current_language -- forcing the language rather
        than auto-detecting improves accuracy and matches
        ARCHITECTURE.md's Language Context Architecture ("After
        activation: All STT... use current_language"), unlike
        detect_wake_word()'s auto-detection, which runs before any
        language is known.

        Publishes TRANSCRIPTION_STARTED before transcribing and
        TRANSCRIPTION_READY (with the transcribed text) after, per
        EVENTS.md's attribution of both to the Whisper Service.
        TRANSCRIPTION_READY triggers utils/scenario_engine.py's
        existing subscription (Milestone 7) automatically.

        Requires this WhisperService to have been constructed with an
        event_bus.

        Args:
            audio: Mono float32 PCM samples at 16kHz.

        Returns:
            The raw transcribed text.

        Raises:
            RuntimeError: if this instance was constructed without an event_bus.
        """
        if self._bus is None:
            raise RuntimeError("transcribe_and_publish() requires WhisperService to be constructed with an event_bus")

        self._bus.publish("TRANSCRIPTION_STARTED", {})

        language_name = self._state.current_language if self._state is not None else None
        whisper_language_code = _NAME_TO_WHISPER_LANGUAGE.get(language_name) if language_name else None
        _, text = self.transcribe(audio, language=whisper_language_code)

        logger.info("Transcribed (language=%s): '%s'", language_name, text)
        self._bus.publish("TRANSCRIPTION_READY", {"text": text})
        return text
