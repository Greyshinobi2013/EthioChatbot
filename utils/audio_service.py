"""Continuous microphone capture for EthioChatbot V2.

Owns the microphone capture thread, per ARCHITECTURE.md's Audio
Service responsibilities: capture microphone audio, buffer audio,
forward audio to Whisper, forward audio to VAD.

This is the piece flagged as missing throughout Milestones 6-12 (no
prior milestone was ever assigned utils/audio_service.py): without a
continuous capture loop, nothing could ever publish TRANSCRIPTION_READY
during a live conversation, and utils/vad_handler.py's interruption
detection had no real audio feeding it outside of tests.

Two distinct buffering concepts are used here, deliberately kept
separate:

- latest_audio_chunk: exactly one small (30ms) raw capture chunk,
  continuously overwritten -- the literal "keep only latest_audio_chunk"
  memory policy from README.md/ARCHITECTURE.md, mirroring
  utils/camera_service.py's latest_frame.
- The per-utterance buffer: a transient, size-bounded accumulation
  used only while actively capturing one wake-word phrase or spoken
  question (from VAD-detected speech onset to VAD-detected trailing
  silence, or a hard maximum duration). It is handed to Whisper and
  discarded immediately once that single utterance completes -- it
  never grows across utterances and is not a "history" in the sense
  the memory policy prohibits, but is a real, necessary buffer because
  Whisper's transcribe() requires a complete utterance, not a
  streaming interface. Its maximum size is bounded by
  max_utterance_seconds, verified in this milestone's tests.
"""
from __future__ import annotations

import threading
from functools import lru_cache
from typing import Callable, List, Optional, Tuple

import numpy as np
import sounddevice as sd

from utils.event_bus import EventBus
from utils.fsm import CONVERSATION_ACTIVE, WAITING_FOR_WAKE_WORD
from utils.logger import get_logger
from utils.state_manager import StateManager
from utils.vad_handler import VAD_FRAME_DURATION_MS, VAD_SAMPLE_RATE, VADHandler
from utils.whisper_utils import WhisperService

logger = get_logger(__name__)

DEFAULT_UTTERANCE_SILENCE_MS = 800
DEFAULT_MAX_UTTERANCE_SECONDS = 8.0
_FALLBACK_CAPTURE_SAMPLE_RATES = (48000, 44100, 32000, 16000)


class AudioServiceError(Exception):
    """Raised when the microphone cannot be opened or read from."""


@lru_cache(maxsize=16)
def _resample_time_axes(num_samples: int, from_rate: int, to_rate: int) -> Tuple[np.ndarray, np.ndarray]:
    """Return (original_times, target_times) for a given resample shape, cached.

    In real usage, process_chunk() calls resample_int16() with the
    same (num_samples, from_rate, to_rate) on every single chunk for
    the life of a capture session (fixed blocksize, fixed rates), so
    recomputing these two np.linspace() arrays from scratch on every
    30ms chunk is pure churn: repeated, short-lived allocations of the
    same shape that (Milestone 13's full-integration memory testing
    found) contribute to glibc allocator arena growth under sustained
    load. Caching them is a pure optimization -- the returned arrays
    are read-only inputs to np.interp() and are never mutated.
    """
    duration = num_samples / from_rate
    target_length = max(0, int(round(duration * to_rate)))
    original_times = np.linspace(0, duration, num=num_samples, endpoint=False)
    target_times = np.linspace(0, duration, num=target_length, endpoint=False)
    return original_times, target_times


def resample_int16(samples: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
    """Resample mono int16 PCM from from_rate to to_rate via linear interpolation.

    Uses NumPy's interp() rather than a dedicated resampling library
    (not in this project's approved technology list) since exact
    audio fidelity is not required for VAD/Whisper input, and the
    chunks involved are small (tens of milliseconds), keeping the
    cost negligible even on Raspberry Pi 4. Works for any rate ratio,
    not just clean integer ones, so it is robust to whatever sample
    rate the actual microphone hardware supports.
    """
    if from_rate == to_rate or len(samples) == 0:
        return samples.astype(np.int16)

    original_times, target_times = _resample_time_axes(len(samples), from_rate, to_rate)
    if len(target_times) == 0:
        return np.array([], dtype=np.int16)

    resampled = np.interp(target_times, original_times, samples.astype(np.float64))
    return resampled.astype(np.int16)


class AudioService:
    """Continuously captures microphone audio and routes it to VAD/Whisper.

    Implements app.py's Service protocol (name, start, stop).
    """

    name = "audio_service"

    def __init__(
        self,
        event_bus: EventBus,
        state_manager: StateManager,
        whisper_service: WhisperService,
        vad_handler: VADHandler,
        device: Optional[int] = None,
        capture_sample_rate: Optional[int] = None,
        utterance_silence_ms: int = DEFAULT_UTTERANCE_SILENCE_MS,
        max_utterance_seconds: float = DEFAULT_MAX_UTTERANCE_SECONDS,
    ) -> None:
        """Args:
            event_bus: Bus used indirectly, via whisper_service/vad_handler.
            state_manager: Shared state read for current_state (to
                decide what to do with each chunk) and written for
                wake_word_status.
            whisper_service: Used for wake-word detection (during
                WAITING_FOR_WAKE_WORD) and transcription (during
                CONVERSATION_ACTIVE).
            vad_handler: Every captured frame is forwarded to its
                process_frame(); it self-gates on current_state, so
                this is safe regardless of what state the robot is in.
            device: sounddevice input device index, or None for the
                system default.
            capture_sample_rate: Force a specific capture rate; None
                probes the device for a working rate (see start()).
            utterance_silence_ms: Trailing silence required to end an
                in-progress utterance capture.
            max_utterance_seconds: Hard cap on utterance length, so a
                continuous talker cannot grow the per-utterance buffer
                unboundedly.
        """
        self._bus = event_bus
        self._state = state_manager
        self._whisper = whisper_service
        self._vad = vad_handler
        self._device = device
        self._requested_sample_rate = capture_sample_rate

        self._silence_frames_required = max(1, round(utterance_silence_ms / VAD_FRAME_DURATION_MS))
        self._max_utterance_frames = max(1, round(max_utterance_seconds * 1000 / VAD_FRAME_DURATION_MS))

        self._stream: Optional[sd.InputStream] = None
        self._native_sample_rate: Optional[int] = None
        self._capture_blocksize: Optional[int] = None

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._chunk_lock = threading.Lock()
        self._latest_audio_chunk: Optional[bytes] = None

        self._utterance_chunks: List[np.ndarray] = []
        self._utterance_active = False
        self._utterance_silent_frames = 0

    @property
    def latest_audio_chunk(self) -> Optional[bytes]:
        """The most recently captured 16kHz mono 16-bit PCM frame, or None.

        Per the memory policy, this is the only audio retained between
        reads -- it is overwritten, never appended to.
        """
        with self._chunk_lock:
            return self._latest_audio_chunk

    def start(self) -> None:
        """Open the microphone and start the capture loop on a background thread.

        Raises:
            AudioServiceError: if no usable input device/sample rate
                combination can be opened.
        """
        native_rate = self._resolve_capture_sample_rate()
        blocksize = max(1, round(native_rate * VAD_FRAME_DURATION_MS / 1000))

        try:
            stream = sd.InputStream(
                device=self._device, samplerate=native_rate, channels=1, dtype="int16", blocksize=blocksize
            )
            stream.start()
        except Exception as exc:
            raise AudioServiceError(f"Could not open microphone (device={self._device}): {exc}") from exc

        self._stream = stream
        self._native_sample_rate = native_rate
        self._capture_blocksize = blocksize

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="AudioThread", daemon=True)
        self._thread.start()
        logger.info(
            "Audio service started (device=%s, capture_rate=%dHz, blocksize=%d, resampling to %dHz)",
            self._device,
            native_rate,
            blocksize,
            VAD_SAMPLE_RATE,
        )

    def stop(self) -> None:
        """Stop the capture loop and release the microphone."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._state.set_wake_word_status("inactive")
        logger.info("Audio service stopped")

    def _resolve_capture_sample_rate(self) -> int:
        """Determine a sample rate the input device actually supports.

        Real microphone hardware often does not support 16kHz capture
        directly (confirmed against this project's own test hardware,
        which only accepts 48kHz); this probes the device's reported
        default first, then a short list of common rates, checking
        each with sounddevice before committing to it.
        """
        if self._requested_sample_rate is not None:
            return self._requested_sample_rate

        try:
            device_info = sd.query_devices(self._device, "input")
            candidate = int(device_info["default_samplerate"])
            sd.check_input_settings(device=self._device, samplerate=candidate, channels=1, dtype="int16")
            return candidate
        except Exception:
            logger.debug("Device default sample rate unusable; probing fallback rates")

        for rate in _FALLBACK_CAPTURE_SAMPLE_RATES:
            try:
                sd.check_input_settings(device=self._device, samplerate=rate, channels=1, dtype="int16")
                return rate
            except Exception:
                continue

        raise AudioServiceError(f"No usable input sample rate found for device={self._device}")

    def _run(self) -> None:
        """Capture loop: read raw chunks continuously until stopped."""
        while not self._stop_event.is_set():
            assert self._stream is not None and self._capture_blocksize is not None
            try:
                raw, _overflowed = self._stream.read(self._capture_blocksize)
            except Exception:
                logger.exception("Audio frame read failed")
                continue
            self.process_chunk(raw.reshape(-1))

    def process_chunk(self, raw_native_rate_int16: np.ndarray) -> None:
        """Resample one captured chunk and route it, per the current FSM state.

        Exposed as a public method, separate from the capture loop, so
        it can be exercised directly in tests without a real
        microphone.

        Args:
            raw_native_rate_int16: Mono int16 PCM at whatever rate the
                device was opened with (self._native_sample_rate).
        """
        native_rate = self._native_sample_rate or VAD_SAMPLE_RATE
        frame_16k = resample_int16(raw_native_rate_int16, native_rate, VAD_SAMPLE_RATE)
        frame_bytes = frame_16k.astype(np.int16).tobytes()

        with self._chunk_lock:
            self._latest_audio_chunk = frame_bytes

        # VAD self-gates on current_state (only acts during PLAYING_AUDIO,
        # and continues an already-started INTERRUPTED silence-wait), so
        # it is safe and correct to always forward every frame to it.
        self._vad.process_frame(frame_bytes)

        current_state = self._state.current_state
        if current_state == WAITING_FOR_WAKE_WORD:
            self._state.set_wake_word_status("listening")
            self._accumulate_utterance(frame_bytes, frame_16k, self._finish_wake_word_utterance)
        elif current_state == CONVERSATION_ACTIVE:
            self._state.set_wake_word_status("inactive")
            self._accumulate_utterance(frame_bytes, frame_16k, self._finish_conversation_utterance)
        else:
            self._state.set_wake_word_status("inactive")
            if self._utterance_active:
                # State changed mid-utterance (e.g. a face was lost);
                # abandon it rather than let it keep growing unseen.
                logger.debug("Abandoning in-progress utterance: state changed to %s", current_state)
                self._reset_utterance()

    def _accumulate_utterance(
        self, frame_bytes: bytes, frame_16k: np.ndarray, on_complete: Callable[[np.ndarray], None]
    ) -> None:
        """Accumulate frames from speech onset to trailing silence (or a hard cap), then hand off.

        The buffer built here is strictly bounded by
        max_utterance_seconds (self._max_utterance_frames) and is
        cleared the instant an utterance completes, regardless of
        outcome -- it never accumulates across utterances.
        """
        is_speech = self._vad.is_speech(frame_bytes)

        if not self._utterance_active:
            if not is_speech:
                return
            self._utterance_active = True
            self._utterance_chunks = [frame_16k]
            self._utterance_silent_frames = 0
            return

        self._utterance_chunks.append(frame_16k)
        self._utterance_silent_frames = 0 if is_speech else self._utterance_silent_frames + 1

        silence_reached = self._utterance_silent_frames >= self._silence_frames_required
        max_length_reached = len(self._utterance_chunks) >= self._max_utterance_frames

        if silence_reached or max_length_reached:
            chunks = self._utterance_chunks
            self._reset_utterance()

            audio_int16 = np.concatenate(chunks)
            audio_float32 = (audio_int16.astype(np.float32) / 32768.0).clip(-1.0, 1.0)

            # Run the (comparatively slow) Whisper call on its own
            # thread so the capture loop never stalls reading the
            # microphone while transcription is in progress.
            worker = threading.Thread(
                target=on_complete, args=(audio_float32,), name="UtteranceProcessingThread", daemon=True
            )
            worker.start()

    def _reset_utterance(self) -> None:
        self._utterance_chunks = []
        self._utterance_active = False
        self._utterance_silent_frames = 0

    def _finish_wake_word_utterance(self, audio_float32: np.ndarray) -> None:
        try:
            self._whisper.process_audio(audio_float32)
        except Exception:
            logger.exception("Error processing wake-word utterance")

    def _finish_conversation_utterance(self, audio_float32: np.ndarray) -> None:
        try:
            self._whisper.transcribe_and_publish(audio_float32)
        except Exception:
            logger.exception("Error transcribing conversation utterance")
