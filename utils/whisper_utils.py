"""Whisper speech recognition and wake-word detection for EthioChatbot V2.

Loads OpenAI Whisper's "base" model once and reuses it, per
ARCHITECTURE.md's Whisper Service responsibilities: wake word
detection, speech transcription, language recognition. The base model
supports English, Amharic, and Arabic while remaining efficient
enough for Raspberry Pi 4.

Phase 1 (wake-word simplification): a single universal wake word,
"Ethiopia", replaces the previous per-language wake-word catalog.
Matching it is activation-only and no longer determines
current_language -- README.md's Language Selection Rule's first
priority tier (Wake Word Language) is now always empty, so
ConversationManager's existing preferred-language/English fallback
tiers apply unconditionally instead. This file only changes wake-word
*matching*; ConversationManager, the FSM, and the scenario/greeting
language systems (still english/amharic/arabic, per
utils/scenario_engine.py and utils/face_enrollment.py's own
SUPPORTED_LANGUAGES) are unaffected.
"""
from __future__ import annotations

import re
import threading
import time
import unicodedata
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import whisper

from utils.event_bus import EventBus
from utils.logger import get_logger
from utils.state_manager import StateManager

logger = get_logger(__name__)

DEFAULT_MODEL_SIZE = "base"

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Failing audio buffers are saved here (as playable WAV files) whenever
# self._model.transcribe() itself raises, so the exact waveform that
# triggered a crash can be inspected/replayed later rather than only
# described by log statistics. Created on first use, not at import time.
DEBUG_AUDIO_DIR = PROJECT_ROOT / "debug_audio"

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

# Phase 1: the sole wake word, replacing the previous per-language
# catalog (WAKE_WORDS dict of english/amharic/arabic phrase lists).
# Activation only -- see detect_wake_word()/process_audio() below for
# why this no longer determines current_language.
UNIVERSAL_WAKE_WORD = "ethiopia"

# Minimum RMS (of normalized [-1, 1] float32 audio) below which an
# utterance is treated as silence/noise-floor rather than real speech and
# rejected before reaching Whisper. Picked well below typical speech RMS
# (commonly > 0.02) but well above true silence/noise-floor level (~0.0001,
# the level observed alongside the "logits ... invalid values: nan" crash
# this threshold was added to prevent).
_MIN_UTTERANCE_RMS = 0.005

# Minimum sample count below which audio is rejected outright, regardless
# of amplitude. Whisper's log-mel spectrogram is computed via a 400-sample
# (25ms at 16kHz) STFT window; audio shorter than that cannot produce even
# one spectral frame, and was found (see _audio_rejection_reason) to be
# the actual condition behind a separate crash --
# "RuntimeError: cannot reshape tensor of 0 elements into shape [1, 0, 8, -1]"
# -- distinct from and occurring after the near-silent-audio NaN-logits
# crash _MIN_UTTERANCE_RMS guards against: this one is about buffer
# *length*, not loudness, and can occur even on healthy-amplitude audio if
# the accumulated utterance buffer itself ends up too short (or empty).
_MIN_UTTERANCE_SAMPLES = 400


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

    Phase 1: activation-only -- carries no language field. Matching
    the universal wake word does not determine current_language (see
    process_audio()); the language field this dataclass previously
    had was removed rather than kept and ignored, so nothing can
    accidentally start relying on a value that no longer means anything.

    Attributes:
        matched_phrase: The wake-word phrase that matched (currently
            always UNIVERSAL_WAKE_WORD).
        transcribed_text: The normalized Whisper transcription.
    """

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

    # Serializes every call into _model.transcribe(), across every
    # WhisperService instance in this process (there is exactly one
    # shared _model, so there must be exactly one lock guarding calls
    # into it). Root-cause investigation confirmed OpenAI Whisper's
    # transcribe()/decode() is not safe to call concurrently on a
    # shared model instance: its KV-cache is implemented via
    # torch.nn.Module.register_forward_hook() on the model's shared
    # attention submodules, which is mutable, non-thread-local state --
    # two concurrent calls' hooks both fire on every forward pass
    # through those submodules regardless of which call triggered it,
    # corrupting each other's cache. A 100+-iteration sequential stress
    # test on this lock-free code produced 0 failures; a concurrent
    # stress test reproduced both previously-observed crash signatures
    # ("ValueError: ... invalid values: nan" and "RuntimeError: cannot
    # reshape tensor of 0 elements...") plus a KeyError on the shared
    # cache and silent cross-contamination between threads' outputs, at
    # a 56-78% failure rate. This lock is deliberately separate from
    # _lock (which only guards the one-time load in get() below) so the
    # two concerns -- "load once" and "run one inference at a time" --
    # stay independently readable.
    _inference_lock = threading.Lock()

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

        The single call point both detect_wake_word() and
        transcribe_and_publish() go through, so audio-safety logging
        and validation live here rather than being duplicated in both
        callers. The actual model call is serialized process-wide via
        _WhisperModel._inference_lock: if this is called concurrently
        (e.g. two utterances completing close together, each handed to
        its own UtteranceProcessingThread by utils/audio_service.py),
        later callers block until the model is free rather than both
        entering self._model.transcribe() at once, which was found to
        corrupt Whisper's shared decoder cache.

        Args:
            audio: Mono float32 PCM samples at WHISPER_SAMPLE_RATE
                (16kHz), normalized to [-1, 1], per Whisper's expected
                input format.
            language: Force a specific Whisper language code (e.g.
                "en"); None lets Whisper auto-detect from the audio.

        Returns:
            (whisper_detected_language_code, raw_transcribed_text).
            ("", "") if the audio was rejected before being handed to
            Whisper (see _audio_rejection_reason), or if
            self._model.transcribe() itself raised (see
            _save_debug_audio) -- callers already treat an empty
            transcription as "no speech recognized", so this needs no
            special-case handling downstream. Whisper crashing is never
            allowed to propagate and take down the capture/utterance
            thread that called this.
        """
        self._log_audio_stats(audio)

        rejection_reason = self._audio_rejection_reason(audio)
        if rejection_reason is not None:
            logger.warning("Rejecting utterance before Whisper: %s", rejection_reason)
            return "", ""

        # Diagnostics immediately before the actual Whisper call: this
        # is audio that already passed every existing guard (non-empty,
        # long enough, no NaN/Inf, not near-silent) -- if a crash still
        # happens on input logged here, this is the exact input to
        # investigate, not a hypothetical one further upstream.
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        duration_ms = len(audio) / WHISPER_SAMPLE_RATE * 1000.0
        rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64)))) if audio.size else 0.0
        logger.info(
            "PRE_TRANSCRIBE_DIAGNOSTIC: shape=%s len=%d dtype=%s rms=%.6f peak=%.6f duration_ms=%.1f language=%s",
            audio.shape,
            len(audio),
            audio.dtype,
            rms,
            peak,
            duration_ms,
            language,
        )

        # Serialize the actual inference call: only one thread may be
        # inside self._model.transcribe() at a time, process-wide (see
        # _WhisperModel._inference_lock's docstring for why). Everything
        # above this point (audio-safety logging/guards) intentionally
        # stays outside the lock, since it does not touch the shared
        # model and would otherwise serialize work that doesn't need to be.
        queue_wait_start = time.perf_counter()
        with _WhisperModel._inference_lock:
            queue_wait_ms = (time.perf_counter() - queue_wait_start) * 1000.0
            logger.info(
                "WHISPER_INFERENCE_STARTED: queue_wait_ms=%.2f len=%d language=%s",
                queue_wait_ms,
                len(audio),
                language,
            )

            inference_start = time.perf_counter()
            try:
                result = self._model.transcribe(audio, language=language, fp16=False)
            except Exception as exc:
                inference_duration_ms = (time.perf_counter() - inference_start) * 1000.0
                logger.info(
                    "WHISPER_INFERENCE_FINISHED: inference_duration_ms=%.2f outcome=crashed",
                    inference_duration_ms,
                )
                logger.exception(
                    "Whisper crashed on an utterance that passed all pre-transcribe guards "
                    "(len=%d rms=%.6f peak=%.6f duration_ms=%.1f language=%s): %s",
                    len(audio),
                    rms,
                    peak,
                    duration_ms,
                    language,
                    exc,
                )
                self._save_debug_audio(audio, language)
                return "", ""

            inference_duration_ms = (time.perf_counter() - inference_start) * 1000.0
            logger.info(
                "WHISPER_INFERENCE_FINISHED: inference_duration_ms=%.2f outcome=success",
                inference_duration_ms,
            )

        return result.get("language", ""), result.get("text", "")

    @staticmethod
    def _save_debug_audio(audio: np.ndarray, language: Optional[str]) -> None:
        """Save an audio buffer that crashed Whisper to DEBUG_AUDIO_DIR as a playable WAV.

        Best-effort: a failure to save (e.g. a read-only filesystem)
        is logged and swallowed rather than raised, since this runs
        inside an already-caught exception handler and must not itself
        crash the caller.
        """
        try:
            DEBUG_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            filename = f"whisper_crash_{time.time():.6f}_lang-{language or 'auto'}.wav"
            path = DEBUG_AUDIO_DIR / filename

            audio_int16 = np.clip(audio.astype(np.float64) * 32768.0, -32768, 32767).astype(np.int16)
            with wave.open(str(path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(WHISPER_SAMPLE_RATE)
                wav_file.writeframes(audio_int16.tobytes())

            logger.warning("Saved failing Whisper input audio to %s for investigation", path)
        except Exception:
            logger.exception("Failed to save debug audio for a Whisper crash (continuing without it)")

    @staticmethod
    def _log_audio_stats(audio: np.ndarray) -> None:
        """Log shape/len/dtype/min/max/rms/NaN-count/Inf-count for every buffer handed to Whisper.

        Whisper has been observed to crash on certain malformed input,
        both on loudness ("ValueError: Expected parameter logits ...
        found invalid values: tensor([[nan, nan, ...]])", near-silent
        audio) and on buffer length ("RuntimeError: cannot reshape
        tensor of 0 elements into shape [1, 0, 8, -1]", too-short/empty
        audio) -- see _audio_rejection_reason for both guards. This
        makes the actual input that triggered either one visible in
        logs without needing to reproduce the failure interactively.
        """
        rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64)))) if audio.size else 0.0
        nan_count = int(np.isnan(audio).sum()) if audio.size else 0
        inf_count = int(np.isinf(audio).sum()) if audio.size else 0
        logger.info(
            "AUDIO_STATS: shape=%s len=%d dtype=%s min=%s max=%s rms=%.6f nan_count=%d inf_count=%d",
            audio.shape,
            len(audio),
            audio.dtype,
            f"{np.min(audio):.6f}" if audio.size else "n/a",
            f"{np.max(audio):.6f}" if audio.size else "n/a",
            rms,
            nan_count,
            inf_count,
        )

    @staticmethod
    def _audio_rejection_reason(audio: np.ndarray) -> Optional[str]:
        """Return why `audio` is unsafe to hand to Whisper, or None if it is safe.

        Two independent, unrelated failure modes are guarded against:
        - Loudness: Whisper's log-mel spectrogram takes log() of the
          STFT magnitude; for all-(near-)zero audio that magnitude can
          be zero, producing -inf/NaN internally that propagates
          through the encoder/decoder as NaN logits ("ValueError:
          Expected parameter logits ... found invalid values").
        - Length: audio shorter than one STFT window (400 samples/25ms
          at 16kHz) -- including exactly empty -- cannot produce even
          one spectral frame, which has been observed to crash with
          "RuntimeError: cannot reshape tensor of 0 elements into
          shape [1, 0, 8, -1]" downstream in the encoder. This can
          happen even on healthy-amplitude audio if the accumulated
          utterance buffer itself ends up too short.
        NaN/Inf already present (e.g. from a capture/resampling fault)
        is also rejected, since it would otherwise reach Whisper as-is.
        All are rejected here before ever reaching self._model.transcribe().
        """
        if audio.size == 0:
            return "audio buffer is empty"
        if audio.size < _MIN_UTTERANCE_SAMPLES:
            return f"audio buffer too short ({audio.size} samples, below minimum {_MIN_UTTERANCE_SAMPLES})"
        if np.isnan(audio).any():
            return "audio contains NaN values"
        if np.isinf(audio).any():
            return "audio contains Inf values"

        rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
        if rms < _MIN_UTTERANCE_RMS:
            return f"audio is silent/near-silent (rms={rms:.6f}, below minimum {_MIN_UTTERANCE_RMS})"

        return None

    def detect_wake_word(self, audio: np.ndarray) -> Optional[WakeWordMatch]:
        """Transcribe audio and check it against the universal wake word.

        Phase 1: a single universal wake word (UNIVERSAL_WAKE_WORD,
        "ethiopia") replaces the previous per-language wake-word
        catalog. Language auto-detection is still used for the
        transcription itself (unchanged), but the result is only
        checked against this one phrase -- it is activation-only and
        does not determine current_language (see process_audio()).

        Every call logs a full WAKE_WORD_EVALUATION record at INFO
        level (raw transcription, normalized transcription, Whisper's
        detected language, the wake word checked, and the match
        outcome) so that live regressions -- e.g. Whisper
        mis-transcribing a spoken wake word close enough to be
        human-recognizable but not an exact/substring match -- are
        diagnosable from logs alone, without reproducing the failure
        interactively.

        Args:
            audio: Mono float32 PCM samples at 16kHz.

        Returns:
            A WakeWordMatch if the universal wake word was recognized,
            else None.
        """
        whisper_language_code, raw_text = self.transcribe(audio, language=None)
        normalized = normalize_text(raw_text)
        detected_language = _WHISPER_LANGUAGE_TO_NAME.get(whisper_language_code, whisper_language_code or "unknown")

        normalized_wake_word = normalize_text(UNIVERSAL_WAKE_WORD)
        is_match = bool(normalized) and (normalized_wake_word == normalized or normalized_wake_word in normalized)
        match = WakeWordMatch(matched_phrase=UNIVERSAL_WAKE_WORD, transcribed_text=normalized) if is_match else None

        if not normalized:
            reason = "transcription is empty after normalization"
        elif match is not None:
            reason = f"matched universal wake word '{UNIVERSAL_WAKE_WORD}'"
        else:
            reason = "universal wake word did not match the normalized transcription"

        logger.info(
            "WAKE_WORD_EVALUATION\n"
            "  RAW_TRANSCRIPTION: %r\n"
            "  NORMALIZED_TEXT: %r\n"
            "  DETECTED_LANGUAGE: %s\n"
            "  EXPECTED_WAKE_WORD: %r\n"
            "  MATCH_RESULT: %s\n"
            "  REASON: %s",
            raw_text,
            normalized,
            detected_language,
            UNIVERSAL_WAKE_WORD,
            "true" if match is not None else "false",
            reason,
        )

        return match

    def process_audio(self, audio: np.ndarray) -> Optional[WakeWordMatch]:
        """Run wake-word detection on an audio buffer and drive the FSM.

        On a match: publishes WAKE_WORD_DETECTED with an empty payload
        (which the Milestone 2 FSM's own subscription advances
        WAITING_FOR_WAKE_WORD -> CONVERSATION_ACTIVE with). Phase 1's
        universal wake word carries no language information, so this
        no longer calls state_manager.set_current_language() itself --
        ConversationManager's existing _on_wake_word_detected()
        subscriber already falls back to the highest-priority active
        user's preferred_language, then "english", whenever the event
        payload has no "language" key (dict.get() returns None,
        exactly as if this had explicitly published one), so that
        fallback now runs unconditionally with no changes needed there.
        On no match: publishes WAKE_WORD_REJECTED, unchanged.

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
            self._bus.publish("WAKE_WORD_DETECTED", {})
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
