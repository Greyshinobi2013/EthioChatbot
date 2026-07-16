"""Whisper speech recognition: singleton model loading, transcription, and
wake-word detection.

Offline execution: the model is downloaded once (cached under
~/.cache/whisper) and reused for the lifetime of the process (README.md
"Load once, Reuse throughout runtime" / "Singleton model loading"). No
network access occurs after the model file is cached locally.
"""
from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Any

import numpy as np
import torch
import whisper

from utils.logger import get_logger

logger = get_logger("whisper_utils")

_model: Any = None
_model_lock = threading.Lock()
_loaded_model_name: str | None = None


def load_model(model_name: str = "medium", use_gpu: bool = True) -> Any:
    """Load (once) and return the singleton Whisper model instance.

    Safe to call repeatedly/concurrently: the model is loaded only once per
    process and reused afterwards. A call with a different model_name after
    the first load is logged and ignored rather than triggering a reload.
    use_gpu=False (config/settings.json "gpu_acceleration") forces CPU even
    when a GPU is available; use_gpu=True still falls back to CPU when no
    GPU is present.
    """
    global _model, _loaded_model_name

    with _model_lock:
        if _model is not None:
            if model_name != _loaded_model_name:
                logger.warning(
                    "Whisper already loaded as '%s'; ignoring request for '%s' "
                    "(singleton model, not reloaded)",
                    _loaded_model_name, model_name,
                )
            return _model

        device = "cuda" if (use_gpu and torch.cuda.is_available()) else "cpu"
        logger.info("Loading Whisper model '%s' on %s...", model_name, device)
        _model = whisper.load_model(model_name, device=device)
        _loaded_model_name = model_name
        logger.info("Whisper model '%s' loaded on %s", model_name, device)
        return _model


def transcribe_audio(
    audio: np.ndarray | Path,
    model_name: str = "medium",
    language: str | None = None,
) -> dict[str, str]:
    """Transcribe audio and return {"text": ..., "language": ...}.

    audio is either a Path to an audio file or a mono float32 numpy array
    sampled at 16kHz (Whisper's expected input), values in [-1, 1].
    language=None lets Whisper auto-detect the spoken language.
    """
    model = load_model(model_name)

    if isinstance(audio, Path):
        audio_data = whisper.load_audio(str(audio))
    else:
        audio_data = np.asarray(audio, dtype=np.float32)

    result = model.transcribe(audio_data, language=language, fp16=False)
    text = str(result.get("text", "")).strip()
    detected_language = str(result.get("language") or language or "en")

    logger.info("Transcribed (language=%s): %r", detected_language, text)
    return {"text": text, "language": detected_language}


_PUNCTUATION_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)


def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace (SCENARIOS.md normalization)."""
    text = text.lower()
    text = _PUNCTUATION_RE.sub("", text)
    return " ".join(text.split())


def detect_wake_word(
    text: str, wake_words: dict[str, list[str]]
) -> tuple[str | None, str | None]:
    """Check normalized text for a configured wake word.

    Returns (language, matched_phrase) for the first language whose wake
    word list appears (as a normalized substring) in text, else (None,
    None). Deterministic substring matching only -- no semantic/AI matching,
    consistent with SCENARIOS.md's "forbidden matching methods".
    """
    normalized = normalize_text(text)
    if not normalized:
        return None, None

    for language, phrases in wake_words.items():
        for phrase in phrases:
            if normalize_text(phrase) in normalized:
                return language, phrase
    return None, None
