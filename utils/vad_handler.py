"""Voice Activity Detection for playback interruption.

Coordinates the interruption workflow (CLAUDE.md "INTERRUPTION RULE"):
response.wav playing -> user speaks -> VAD detects speech -> pause
response -> play please_wait.wav -> wait for silence -> resume response
from its exact paused position.

Unlike camera_service/audio_service, this module does not hold the
microphone open for the whole application lifetime: it only needs the mic
while a response is actually playing (PLAYING_AUDIO/INTERRUPTED), and
opening it only then avoids contending with audio_service's own
continuously-open wake-word listening stream for the same hardware device.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
import webrtcvad

from utils.event_bus import publish
from utils.logger import get_logger
from utils.playback import notify_user, pause_audio, resume_audio
from utils.state_manager import AppState

logger = get_logger("vad_handler")

AUDIO_ROOT = Path("audio")
DEFAULT_LANGUAGE = "english"
NOTIFICATION_AUDIO_NAME = "please_wait.wav"

FRAME_MS = 30
VALID_SAMPLE_RATES = (8000, 16000, 32000, 48000)
FALLBACK_SAMPLE_RATE = 48000
SILENCE_HANGOVER_SECONDS = 1.0


def start_vad(aggressiveness: int = 2) -> webrtcvad.Vad:
    """Create a WebRTC VAD instance. aggressiveness: 0 (least) - 3 (most sensitive)."""
    vad = webrtcvad.Vad(aggressiveness)
    logger.info("VAD initialized (aggressiveness=%s)", aggressiveness)
    return vad


def is_speech(frame: np.ndarray, sample_rate: int, vad: webrtcvad.Vad) -> bool:
    """Return True if a mono float32 frame contains speech.

    frame must hold exactly FRAME_MS worth of samples at sample_rate --
    WebRTC VAD only accepts 10/20/30ms frames at 8k/16k/32k/48kHz.
    """
    pcm16 = np.clip(frame * 32767.0, -32768, 32767).astype(np.int16).tobytes()
    return vad.is_speech(pcm16, sample_rate)


def _pick_sample_rate() -> int:
    try:
        native = int(sd.query_devices(kind="input")["default_samplerate"])
    except Exception:
        return FALLBACK_SAMPLE_RATE
    return native if native in VALID_SAMPLE_RATES else FALLBACK_SAMPLE_RATE


def _notification_path(state: AppState) -> Path:
    language = state.current_language or DEFAULT_LANGUAGE
    return AUDIO_ROOT / language / NOTIFICATION_AUDIO_NAME


def _run_interruption_session(state: AppState, stop_event: threading.Event, vad: webrtcvad.Vad) -> None:
    """Watch the mic for the duration of one PLAYING_AUDIO episode.

    Opens the microphone, monitors for interruptions until playback
    naturally finishes (state leaves PLAYING_AUDIO/INTERRUPTED), then
    closes the microphone again.
    """
    sample_rate = _pick_sample_rate()
    frame_samples = int(sample_rate * FRAME_MS / 1000)

    # audio_service releases the microphone quickly on a PLAYING_AUDIO
    # transition, but not instantly -- a short retry absorbs that brief
    # handoff window instead of giving up on the first busy-device error.
    stream = None
    last_error: Exception | None = None
    for attempt in range(5):
        if stop_event.is_set():
            return
        try:
            stream = sd.InputStream(
                samplerate=sample_rate, channels=1, dtype="float32", blocksize=frame_samples
            )
            stream.start()
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(0.15)

    if stream is None:
        logger.error("Could not open microphone for VAD after retries: %s", last_error)
        state.set_status("vad_status", "ERROR")
        return

    state.set_status("vad_status", "ACTIVE")
    logger.info("VAD monitoring session started (sample_rate=%s, frame_ms=%s)", sample_rate, FRAME_MS)

    interrupted = False
    last_speech_time = 0.0

    try:
        while not stop_event.is_set() and state.current_state in ("PLAYING_AUDIO", "INTERRUPTED"):
            frames, overflowed = stream.read(frame_samples)
            if overflowed:
                logger.warning("VAD microphone input overflowed")

            speech = is_speech(frames[:, 0], sample_rate, vad)

            if not interrupted:
                if speech:
                    logger.info("Interruption detected")
                    publish("INTERRUPTION_DETECTED")
                    pause_audio()
                    state.set_status("playback_status", "PAUSED")
                    state.set_state("INTERRUPTED")
                    interrupted = True
                    last_speech_time = time.monotonic()

                    notice_path = _notification_path(state)
                    if notice_path.exists():
                        try:
                            notify_user(notice_path, wait=True)
                        except Exception:
                            logger.exception("Failed to play interruption notice: %s", notice_path)
                    else:
                        logger.error("Interruption notice audio not found: %s", notice_path)
            else:
                if speech:
                    last_speech_time = time.monotonic()
                elif time.monotonic() - last_speech_time >= SILENCE_HANGOVER_SECONDS:
                    logger.info("Silence detected; resuming playback")
                    publish("INTERRUPTION_CLEARED")
                    resume_audio()
                    state.set_status("playback_status", "PLAYING")
                    state.set_state("PLAYING_AUDIO")
                    interrupted = False
    except Exception:
        logger.exception("VAD monitoring session crashed")
        state.set_status("vad_status", "ERROR")
    finally:
        stream.stop()
        stream.close()
        state.set_status("vad_status", "IDLE")
        logger.info("VAD monitoring session ended")


def monitor_interruptions(state: AppState, stop_event: threading.Event) -> None:
    """Background thread target: alive for the process lifetime, but only
    opens the microphone for the duration of each PLAYING_AUDIO episode.
    """
    vad = start_vad(state.config["vad_aggressiveness"])
    state.set_status("vad_status", "IDLE")

    while not stop_event.is_set():
        if state.current_state != "PLAYING_AUDIO":
            time.sleep(0.1)
            continue
        _run_interruption_session(state, stop_event, vad)
