"""Continuous microphone monitoring: wake-word detection and, once a
conversation is active, question transcription (both via Whisper).

Runs as a single background thread started once at application bootstrap.
Unlike camera_service (whose camera really is opened once and held for the
process lifetime), this service opens the microphone only for the
duration of each WAITING_FOR_WAKE_WORD/CONVERSATION_ACTIVE session and
closes it the moment the state leaves both -- this hardware's ALSA device
does not support two simultaneous opens, and vad_handler needs the same
device during PLAYING_AUDIO/INTERRUPTED, so the two must never both hold
it open at once (found via live testing: vad_handler's stream open failed
outright while this service's stream was left open across state changes).
"""
from __future__ import annotations

import threading
import time

import numpy as np
import sounddevice as sd

from utils.event_bus import publish
from utils.logger import get_logger
from utils.state_manager import AppState
from utils.whisper_utils import detect_wake_word, load_model, transcribe_audio

logger = get_logger("audio_service")

WHISPER_SAMPLE_RATE = 16000
CHUNK_SECONDS = 3.0
SUB_CHUNK_SECONDS = 0.3
FALLBACK_DEVICE_SAMPLE_RATE = 48000

# Internal language keys (config/settings.json, SCENARIOS.md) to Whisper's
# ISO-639-1-style language hints, used during CONVERSATION_ACTIVE now that
# the language is already known from LANGUAGE_SELECTION -- this improves
# transcription accuracy over auto-detecting every question from scratch.
LANGUAGE_TO_WHISPER_CODE = {"english": "en", "amharic": "am", "arabic": "ar"}

LISTENING_STATES = ("WAITING_FOR_WAKE_WORD", "CONVERSATION_ACTIVE")


def _resample_to_16k(audio: np.ndarray, native_rate: int) -> np.ndarray:
    """Linearly resample mono float32 audio from native_rate to 16kHz.

    scipy/librosa are not in the approved technology stack, so this uses
    plain NumPy interpolation -- adequate quality for speech recognition,
    which is all Whisper needs here.
    """
    if native_rate == WHISPER_SAMPLE_RATE:
        return audio
    duration = len(audio) / native_rate
    target_len = int(round(duration * WHISPER_SAMPLE_RATE))
    original_times = np.linspace(0.0, duration, num=len(audio), endpoint=False)
    target_times = np.linspace(0.0, duration, num=target_len, endpoint=False)
    return np.interp(target_times, original_times, audio).astype(np.float32)


def _read_chunk_responsive(
    stream: sd.InputStream,
    state: AppState,
    stop_event: threading.Event,
    chunk_frames: int,
    sub_chunk_frames: int,
) -> np.ndarray | None:
    """Read chunk_frames total, in small sub-chunks, checking state/stop
    between each so a state change is noticed within ~SUB_CHUNK_SECONDS
    instead of up to CHUNK_SECONDS.

    Without this, a blocking read() of the full chunk can hold the
    microphone open for up to CHUNK_SECONDS after PLAYING_AUDIO starts,
    racing vad_handler for the same device (found via live testing: with a
    single 3s read, vad_handler's stream-open consistently lost that
    race). Returns None if interrupted early -- the caller should treat
    that as "nothing to process" and let its own loop condition exit.
    """
    collected = []
    total = 0
    overflowed_any = False
    while total < chunk_frames:
        if stop_event.is_set() or state.current_state not in LISTENING_STATES:
            return None
        frames_to_read = min(sub_chunk_frames, chunk_frames - total)
        frames, overflowed = stream.read(frames_to_read)
        overflowed_any = overflowed_any or overflowed
        collected.append(frames)
        total += frames_to_read
    if overflowed_any:
        logger.warning("Microphone input overflowed")
    return np.concatenate(collected, axis=0)


def _run_listening_session(
    state: AppState,
    stop_event: threading.Event,
    whisper_model_name: str,
    native_rate: int,
    set_wake_status,
) -> None:
    """Open the mic and handle wake-word/question listening for as long as
    state stays in WAITING_FOR_WAKE_WORD or CONVERSATION_ACTIVE, then
    close the mic again (so vad_handler can use the device meanwhile).
    """
    chunk_frames = int(native_rate * CHUNK_SECONDS)
    sub_chunk_frames = max(1, int(native_rate * SUB_CHUNK_SECONDS))

    try:
        stream = sd.InputStream(samplerate=native_rate, channels=1, dtype="float32")
        stream.start()
    except Exception:
        logger.exception("Could not open microphone")
        state.set_status("microphone_status", "ERROR")
        return

    state.set_status("microphone_status", "ACTIVE")
    logger.info("Microphone opened (native_sample_rate=%s)", native_rate)

    try:
        while not stop_event.is_set() and state.current_state in LISTENING_STATES:
            current_state = state.current_state
            set_wake_status("LISTENING" if current_state == "WAITING_FOR_WAKE_WORD" else "IDLE")

            frames = _read_chunk_responsive(stream, state, stop_event, chunk_frames, sub_chunk_frames)
            if frames is None:
                break  # state changed away from a listening state mid-read

            audio = _resample_to_16k(frames[:, 0].astype(np.float32), native_rate)

            if current_state == "WAITING_FOR_WAKE_WORD":
                try:
                    result = transcribe_audio(audio, model_name=whisper_model_name)
                except Exception:
                    logger.exception("Wake-word transcription failed")
                    continue

                language, phrase = detect_wake_word(result["text"], state.config["wake_words"])
                if language is not None:
                    logger.info("Wake word detected: '%s' (language=%s)", phrase, language)
                    set_wake_status("DETECTED")
                    publish("WAKE_WORD_DETECTED", language=language, phrase=phrase, text=result["text"])
                elif result["text"]:
                    logger.info("Speech heard but no wake word matched: %r", result["text"])
                    publish("WAKE_WORD_REJECTED", text=result["text"])

            else:  # CONVERSATION_ACTIVE: transcribe the question itself
                whisper_language = LANGUAGE_TO_WHISPER_CODE.get(state.current_language)
                publish("TRANSCRIPTION_STARTED")
                try:
                    result = transcribe_audio(
                        audio, model_name=whisper_model_name, language=whisper_language
                    )
                except Exception:
                    logger.exception("Conversation transcription failed")
                    continue

                publish("TRANSCRIPTION_READY", text=result["text"], language=result["language"])
                if result["text"]:
                    logger.info("Transcribed question: %r", result["text"])
    except Exception:
        logger.exception("Audio listening session crashed")
        state.set_status("microphone_status", "ERROR")
    finally:
        stream.stop()
        stream.close()
        state.set_status("microphone_status", "STOPPED")
        logger.info("Microphone released")


def run_audio_service(state: AppState, stop_event: threading.Event) -> None:
    """Background thread target for microphone monitoring.

    A failure here is caught and logged rather than propagated, so it
    cannot bring down the rest of the application (ARCHITECTURE.md
    "Failure Isolation").
    """
    whisper_model_name = state.config["whisper_model"]

    try:
        load_model(whisper_model_name, use_gpu=state.config.get("gpu_acceleration", True))
    except Exception:
        logger.exception("Failed to load Whisper model; wake-word detection disabled")
        state.set_status("microphone_status", "ERROR")
        return

    try:
        native_rate = int(sd.query_devices(kind="input")["default_samplerate"])
    except Exception:
        logger.warning(
            "Could not query default input device sample rate; falling back to %s",
            FALLBACK_DEVICE_SAMPLE_RATE,
        )
        native_rate = FALLBACK_DEVICE_SAMPLE_RATE

    last_wake_status: str | None = None

    def set_wake_status(value: str) -> None:
        nonlocal last_wake_status
        if value != last_wake_status:
            state.set_status("wake_word_status", value)
            last_wake_status = value

    while not stop_event.is_set():
        if state.current_state not in LISTENING_STATES:
            set_wake_status("IDLE")
            time.sleep(0.2)
            continue
        _run_listening_session(state, stop_event, whisper_model_name, native_rate, set_wake_status)
