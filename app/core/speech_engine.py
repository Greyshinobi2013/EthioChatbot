"""
Speech input handling: offline transcription (Whisper), wake-word
detection, and voice-activity detection (VAD) used for barge-in /
interruption handling during audio playback.

Three distinct jobs live here, kept in one module because they all
read from the same microphone stream:

1. WakeWordListener   - short recording -> Whisper transcript -> match
                         against configured wake words per language.
2. VoiceActivityMonitor - lightweight, *fast* "is someone talking right
                         now" signal, used to interrupt playback. This
                         deliberately does NOT use Whisper (too slow for
                         real-time barge-in); it uses webrtcvad if
                         available, falling back to a simple RMS-energy
                         gate.
3. Transcriber        - thin wrapper around whisper for one-off
                         transcription of a captured audio buffer.

All three depend only on locally-installed models/libraries (Whisper
run with a local model checkpoint, webrtcvad is a pure offline VAD) to
satisfy the "no internet dependency" requirement.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from app.core.config import SETTINGS, get_logger

logger = get_logger(__name__)

try:
    import sounddevice as sd
except (ImportError, OSError):  # pragma: no cover
    # ImportError: package not installed.
    # OSError: package is installed but the native PortAudio library
    # it binds to isn't present on this system (common on minimal
    # Linux images/containers) -- sounddevice raises OSError at import
    # time in that case, not ImportError, so both must be caught here.
    sd = None

try:
    import whisper as openai_whisper
except ImportError:  # pragma: no cover
    openai_whisper = None

try:
    import webrtcvad
except ImportError:  # pragma: no cover
    webrtcvad = None


# ---------------------------------------------------------------------------
# Whisper transcription
# ---------------------------------------------------------------------------

class Transcriber:
    """Loads a local Whisper model once and reuses it.

    Loading is the expensive part (multi-second model load for
    base/small), so this class is meant to be instantiated once per
    process (e.g. cached in Streamlit session_state) rather than per
    call.
    """

    def __init__(self, model_size: Optional[str] = None):
        if openai_whisper is None:
            raise ImportError(
                "The 'openai-whisper' package is required for offline "
                "speech recognition. Install it and a local model "
                "checkpoint per the README."
            )
        self.model_size = model_size or SETTINGS.whisper_model_size
        logger.info("Loading Whisper model '%s'...", self.model_size)
        self.model = openai_whisper.load_model(self.model_size)
        logger.info("Whisper model loaded.")

    def transcribe(self, audio: np.ndarray, language: Optional[str] = None) -> str:
        """`audio` must be float32 mono PCM at 16kHz, range [-1, 1]."""
        result = self.model.transcribe(
            audio.astype(np.float32),
            language=language,
            fp16=False,
        )
        return result.get("text", "").strip()


# ---------------------------------------------------------------------------
# Audio capture helper
# ---------------------------------------------------------------------------

def record_audio(seconds: float, sample_rate: int = None) -> np.ndarray:
    """Blocking microphone capture, returns float32 mono samples."""
    if sd is None:
        raise ImportError("sounddevice is required for microphone capture.")
    sample_rate = sample_rate or SETTINGS.sample_rate
    frames = sd.rec(int(seconds * sample_rate), samplerate=sample_rate, channels=1, dtype="float32")
    sd.wait()
    return frames.flatten()


# ---------------------------------------------------------------------------
# Wake word detection
# ---------------------------------------------------------------------------

@dataclass
class WakeWordResult:
    matched: bool
    language: Optional[str]
    transcript: str


class WakeWordListener:
    """Records a short clip, transcribes it, and checks it against the
    wake words configured per language in dialog_config.json.

    Matching is a simple case-insensitive substring check. This is
    deliberately simple (vs. a dedicated keyword-spotting model)
    because Whisper's transcript for a 2-4 word utterance is fast and
    accurate enough on a 'base' model, and it lets the same listener
    handle multiple languages/scripts (e.g. Amharic) without a separate
    model per wake word.
    """

    def __init__(self, transcriber: Transcriber, languages_config: dict):
        self.transcriber = transcriber
        self.languages_config = languages_config

    def listen_once(self, seconds: Optional[float] = None) -> WakeWordResult:
        seconds = seconds or SETTINGS.wake_word_listen_seconds
        audio = record_audio(seconds)
        transcript = self.transcriber.transcribe(audio)
        return self.match(transcript)

    def match(self, transcript: str) -> WakeWordResult:
        normalized = transcript.lower().strip()
        for lang_code, lang_cfg in self.languages_config.items():
            candidates = list(lang_cfg.get("wake_words", []))
            candidates += list(lang_cfg.get("wake_words_native", []))
            for word in candidates:
                if word.lower() in normalized:
                    return WakeWordResult(matched=True, language=lang_code, transcript=transcript)
        return WakeWordResult(matched=False, language=None, transcript=transcript)


# ---------------------------------------------------------------------------
# Voice Activity Detection (interruption handling)
# ---------------------------------------------------------------------------

class VoiceActivityMonitor:
    """Continuously samples the microphone in a background thread and
    raises an `on_speech_detected` callback as soon as sustained voice
    activity is seen -- this is what lets the chatbot pause playback
    the moment the user starts talking, instead of waiting for a full
    Whisper transcription cycle.

    Uses webrtcvad when available (frame-level voiced/unvoiced
    classification, very low latency). Falls back to a simple
    RMS-energy threshold if webrtcvad isn't installed, which is less
    accurate (will trigger on loud non-speech noise) but keeps the
    feature working without the extra dependency.
    """

    def __init__(
        self,
        on_speech_detected: Callable[[], None],
        sample_rate: Optional[int] = None,
    ):
        self.on_speech_detected = on_speech_detected
        self.sample_rate = sample_rate or SETTINGS.sample_rate
        self.frame_ms = SETTINGS.vad_frame_ms
        self.frame_samples = int(self.sample_rate * self.frame_ms / 1000)

        self._vad = None
        if webrtcvad is not None:
            self._vad = webrtcvad.Vad(SETTINGS.vad_aggressiveness)
        else:
            logger.warning(
                "webrtcvad not installed; falling back to RMS-energy "
                "interruption detection (less robust to background noise)."
            )

        self._stop_event = threading.Event()
        self._pause_event = threading.Event()  # when set, monitor ignores audio
        self._thread: Optional[threading.Thread] = None
        self._consecutive_voiced = 0

    # -- public control -----------------------------------------------------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("VoiceActivityMonitor started.")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("VoiceActivityMonitor stopped.")

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def suppress(self) -> None:
        """Temporarily ignore audio (e.g. while the system itself is
        about to speak, to avoid self-triggering on bleed/echo)."""
        self._pause_event.set()
        self._consecutive_voiced = 0

    def resume_monitoring(self) -> None:
        self._pause_event.clear()
        self._consecutive_voiced = 0

    # -- internals ------------------------------------------------------------

    def _run(self) -> None:
        if sd is None:
            raise ImportError("sounddevice is required for VAD monitoring.")

        block_queue: "queue.Queue[np.ndarray]" = queue.Queue()

        def callback(indata, frames, time_info, status):
            if status:
                logger.debug("sounddevice status: %s", status)
            block_queue.put(indata.copy())

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self.frame_samples,
            callback=callback,
        ):
            while not self._stop_event.is_set():
                try:
                    block = block_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                if self._pause_event.is_set():
                    self._consecutive_voiced = 0
                    continue

                voiced = self._is_voiced(block)
                if voiced:
                    self._consecutive_voiced += 1
                else:
                    self._consecutive_voiced = 0

                if self._consecutive_voiced >= SETTINGS.interruption_confirm_frames:
                    self._consecutive_voiced = 0
                    try:
                        self.on_speech_detected()
                    except Exception:
                        logger.exception("Error in on_speech_detected callback")

    def _is_voiced(self, block: np.ndarray) -> bool:
        pcm_bytes = block.tobytes()
        if self._vad is not None:
            # webrtcvad requires exact 10/20/30ms frames at supported rates
            try:
                return self._vad.is_speech(pcm_bytes, self.sample_rate)
            except Exception:
                pass  # fall through to energy-based check on bad frame size

        # RMS-energy fallback (normalize int16 -> [-1, 1] first)
        samples = block.astype(np.float32) / 32768.0
        rms = float(np.sqrt(np.mean(np.square(samples)))) if samples.size else 0.0
        return rms >= SETTINGS.interruption_rms_threshold
