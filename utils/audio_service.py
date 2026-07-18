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
import time
from functools import lru_cache
from typing import Callable, List, Optional, Tuple

import numpy as np
import sounddevice as sd

from utils.event_bus import EventBus
from utils.fsm import CONVERSATION_ACTIVE, WAITING_FOR_WAKE_WORD
from utils.logger import get_logger
from utils.noise_suppression import NoiseSuppressor
from utils.state_manager import StateManager
from utils.vad_handler import VAD_FRAME_DURATION_MS, VAD_SAMPLE_RATE, VADHandler
from utils.whisper_utils import WhisperService

logger = get_logger(__name__)

DEFAULT_UTTERANCE_SILENCE_MS = 800
DEFAULT_MAX_UTTERANCE_SECONDS = 8.0
_FALLBACK_CAPTURE_SAMPLE_RATES = (48000, 44100, 32000, 16000)

# Known-working input device indices on this project's own hardware
# (confirmed via direct sd.check_input_settings() investigation: PortAudio's
# own "system default" device selection was found to raise
# PortAudioError [PaErrorCode -9999] "Unanticipated host error" / ALSA
# buffer setup failure, so device=None can no longer be trusted -- these
# are tried, in order, whenever the configured device is unset or fails
# validation. Device indices on this ALSA/PipeWire setup are not stable
# across process runs, so every candidate is still validated with
# sd.check_input_settings() before use rather than assumed correct.
_FALLBACK_INPUT_DEVICES: Tuple[int, ...] = (3, 4, 6, 7)

# A stream that fails this many consecutive reads is treated as broken
# (not a one-off transient blip) and is closed and reopened rather than
# retried forever. Sandboxed/virtualized audio backends (this project's
# own dev environment runs PipeWire emulating ALSA) have been observed
# to occasionally enter a bad stream state after a successful open;
# without this recovery path, the capture thread would otherwise loop
# on .read() indefinitely, unable to ever produce audio again.
_MAX_CONSECUTIVE_READ_FAILURES = 5
_READ_FAILURE_BACKOFF_SECONDS = 0.5


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


def _int16_rms(samples: np.ndarray) -> float:
    """RMS amplitude of int16 PCM samples, in raw int16 units (0-32768 scale).

    Shared by the temporary gain-diagnostic logging in process_chunk()
    and _accumulate_utterance() so "RMS before/after resampling" and
    "RMS before/after normalization" are computed identically and are
    directly comparable.
    """
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))


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
        noise_suppressor: Optional[NoiseSuppressor] = None,
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
            noise_suppressor: Applied to each raw captured chunk before
                resampling/VAD/accumulation (Microphone -> AudioService
                -> RNNoise -> VADHandler). Optional and defaults to
                None, in which case AudioService behaves exactly as it
                did before noise suppression existed -- when provided
                but disabled (config/settings.json's
                noise_suppression_enabled=false), its own process()
                is still called but always returns its input unchanged,
                which is equivalent but keeps the diagnostic logging
                (NOISE_SUPPRESSION_ENABLED/AUDIO_PATH) consistent.
            device: sounddevice input device index to prefer (e.g.
                config/settings.json's audio_input_device). Always
                validated with sd.check_input_settings() before use;
                if it is None or fails validation, _FALLBACK_INPUT_DEVICES
                is probed in order and the first working device is
                used instead -- PortAudio's own "system default" device
                (device=None passed straight to sd.InputStream) is not
                relied on, since it was found to raise
                PortAudioError [PaErrorCode -9999] on this project's
                own ALSA/PipeWire setup.
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
        self._noise_suppressor = noise_suppressor
        self._device = device
        self._requested_sample_rate = capture_sample_rate

        self._silence_frames_required = max(1, round(utterance_silence_ms / VAD_FRAME_DURATION_MS))
        self._max_utterance_frames = max(1, round(max_utterance_seconds * 1000 / VAD_FRAME_DURATION_MS))

        self._stream: Optional[sd.InputStream] = None
        self._native_sample_rate: Optional[int] = None
        self._capture_blocksize: Optional[int] = None
        # The device actually validated and opened, which may differ from
        # self._device (the configured preference) if that preference was
        # None or failed validation and a fallback device was used instead.
        self._resolved_device: Optional[int] = None

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
        self._open_stream()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="AudioThread", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the capture loop and release the microphone."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        self._close_stream()
        self._state.set_wake_word_status("inactive")
        logger.info("Audio service stopped")

    def _open_stream(self) -> None:
        """Resolve a working device+sample rate and open+start the InputStream.

        Called by start(), and again by the capture loop's recovery
        path (see _run()) when repeated reads fail -- so a stream that
        has entered a broken state gets a real chance to recover
        instead of looping on a dead stream object forever. Each call
        re-validates the device from scratch (see
        _resolve_capture_device_and_rate()), so a device that has
        stopped working since the last open is detected here rather
        than surfacing as a raw PortAudioError from stream.read().

        Raises:
            AudioServiceError: if no usable device/rate combination can
                be opened.
        """
        device_index, native_rate = self._resolve_capture_device_and_rate()
        blocksize = max(1, round(native_rate * VAD_FRAME_DURATION_MS / 1000))
        device_name = self._describe_device(device_index)

        logger.info(
            "Opening microphone InputStream: device=%s [%s], channels=1, samplerate=%dHz, blocksize=%d, dtype=int16",
            device_index,
            device_name,
            native_rate,
            blocksize,
        )
        try:
            stream = sd.InputStream(
                device=device_index, samplerate=native_rate, channels=1, dtype="int16", blocksize=blocksize
            )
            stream.start()
        except Exception as exc:
            logger.error(
                "InputStream failed to open (device=%s [%s], channels=1, samplerate=%dHz, blocksize=%d, "
                "dtype=int16): %s: %s",
                device_index,
                device_name,
                native_rate,
                blocksize,
                type(exc).__name__,
                exc,
                exc_info=True,
            )
            raise AudioServiceError(f"Could not open microphone (device={device_index} [{device_name}]): {exc}") from exc

        logger.info(
            "InputStream opened and started successfully (selected device index=%s [%s], samplerate=%.0fHz)",
            device_index,
            device_name,
            stream.samplerate,
        )

        self._stream = stream
        self._resolved_device = device_index
        self._native_sample_rate = native_rate
        self._capture_blocksize = blocksize
        logger.info(
            "Audio service started (device=%s [%s], capture_rate=%dHz, blocksize=%d, resampling to %dHz)",
            device_index,
            device_name,
            native_rate,
            blocksize,
            VAD_SAMPLE_RATE,
        )

    def _close_stream(self) -> None:
        """Stop and close the current InputStream, if any, so a fresh one can be opened."""
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                logger.exception("Error closing microphone stream")
            self._stream = None
            self._resolved_device = None

    def _resolve_capture_device_and_rate(self) -> Tuple[int, int]:
        """Pick a working input device and sample rate.

        Tries the configured device (self._device, e.g. from
        config/settings.json's audio_input_device) first, then falls
        back to _FALLBACK_INPUT_DEVICES in order, validating every
        candidate with sd.check_input_settings() before use -- never
        passing device=None straight to sd.InputStream(), since
        PortAudio's own "system default" selection was found to raise
        PortAudioError [PaErrorCode -9999] (ALSA buffer setup failure)
        on this project's own ALSA/PipeWire setup.

        Raises:
            AudioServiceError: if no candidate device/rate combination
                validates successfully.
        """
        candidates: List[int] = []
        if self._device is not None:
            candidates.append(self._device)
        for fallback_device in _FALLBACK_INPUT_DEVICES:
            if fallback_device not in candidates:
                candidates.append(fallback_device)

        attempted_errors: List[str] = []
        for device_index in candidates:
            try:
                rate = self._probe_device_sample_rate(device_index)
                return device_index, rate
            except AudioServiceError as exc:
                attempted_errors.append(f"device={device_index}: {exc}")
                logger.warning("Input device %s failed validation: %s", device_index, exc)

        raise AudioServiceError(
            f"No usable input device found (tried {candidates}): {'; '.join(attempted_errors)}"
        )

    def _probe_device_sample_rate(self, device_index: int) -> int:
        """Validate one device with sd.check_input_settings(), returning a working sample rate.

        Real microphone hardware often does not support 16kHz capture
        directly (confirmed against this project's own test hardware,
        which only accepts 48kHz); this probes the device's reported
        default first, then a short list of common rates, checking
        each with sounddevice before committing to it.

        Raises:
            AudioServiceError: if this device supports none of the
                candidate rates (including its own reported default).
        """
        if self._requested_sample_rate is not None:
            sd.check_input_settings(
                device=device_index, samplerate=self._requested_sample_rate, channels=1, dtype="int16"
            )
            return self._requested_sample_rate

        try:
            device_info = sd.query_devices(device_index, "input")
            candidate = int(device_info["default_samplerate"])
            sd.check_input_settings(device=device_index, samplerate=candidate, channels=1, dtype="int16")
            return candidate
        except Exception:
            logger.debug("Device %s default sample rate unusable; probing fallback rates", device_index)

        for rate in _FALLBACK_CAPTURE_SAMPLE_RATES:
            try:
                sd.check_input_settings(device=device_index, samplerate=rate, channels=1, dtype="int16")
                return rate
            except Exception:
                continue

        raise AudioServiceError(f"No usable sample rate found for device={device_index}")

    @staticmethod
    def _describe_device(device_index: int) -> str:
        """Return the human-readable device name for logging, or 'unknown' if it can't be queried."""
        try:
            return str(sd.query_devices(device_index)["name"])
        except Exception:
            return "unknown"

    def _run(self) -> None:
        """Capture loop: read raw chunks continuously until stopped, recovering from stream failures.

        If self._stream is None (either never opened, or just closed
        by the recovery path below), this tries to open a fresh one
        every pass rather than asserting -- that would otherwise crash
        the thread the moment a broken stream gets closed.
        """
        consecutive_failures = 0
        while not self._stop_event.is_set():
            if self._stream is None:
                try:
                    self._open_stream()
                    consecutive_failures = 0
                    logger.info("Microphone stream opened successfully; resuming capture")
                except AudioServiceError:
                    logger.exception("Still unable to open microphone stream; will keep retrying")
                    time.sleep(_READ_FAILURE_BACKOFF_SECONDS)
                continue

            try:
                raw, overflowed = self._stream.read(self._capture_blocksize)
            except Exception as exc:
                consecutive_failures += 1
                logger.error(
                    "Audio frame read failed (failure %d/%d before reopening; device=%s, "
                    "samplerate=%s, blocksize=%s, dtype=int16, channels=1): %s: %s",
                    consecutive_failures,
                    _MAX_CONSECUTIVE_READ_FAILURES,
                    self._resolved_device,
                    self._native_sample_rate,
                    self._capture_blocksize,
                    type(exc).__name__,
                    exc,
                    exc_info=True,
                )
                if consecutive_failures >= _MAX_CONSECUTIVE_READ_FAILURES:
                    logger.warning(
                        "%d consecutive read failures; closing and reopening the microphone stream",
                        consecutive_failures,
                    )
                    self._close_stream()
                    consecutive_failures = 0
                time.sleep(_READ_FAILURE_BACKOFF_SECONDS)
                continue

            consecutive_failures = 0
            if overflowed:
                logger.debug("Audio input buffer overflowed; some samples may have been dropped")
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

        # Guard against a short/partial device read: resample_int16()'s
        # output length is only correct (exactly one VAD frame's worth of
        # 16kHz samples) when given exactly self._capture_blocksize
        # native-rate samples -- by construction, blocksize is always
        # computed so that resampling it yields a clean, exact frame
        # length with no rounding surprises. A mismatch here (which
        # sd.InputStream.read() is not supposed to produce, but this
        # project's own PipeWire/ALSA setup has shown real instability
        # elsewhere -- see _open_stream()'s recovery logic) can otherwise
        # silently produce a too-short or zero-length resampled frame:
        # WebRTC VAD requires an exact frame size and would raise on a
        # malformed one, and a 0-length frame accumulated into an
        # utterance buffer is exactly the condition behind
        # "RuntimeError: cannot reshape tensor of 0 elements into shape
        # [1, 0, 8, -1]" once handed to Whisper. Skipping the frame here
        # (never resampled, never forwarded to VAD/accumulation) closes
        # that off at the source rather than downstream.
        if self._capture_blocksize is not None and len(raw_native_rate_int16) != self._capture_blocksize:
            logger.warning(
                "AUDIO_CHUNK_DIAGNOSTIC: dropping malformed capture chunk (got %d samples, expected %d, "
                "native_rate=%dHz) -- likely a short/partial device read; not forwarded to VAD or "
                "utterance accumulation",
                len(raw_native_rate_int16),
                self._capture_blocksize,
                native_rate,
            )
            return

        # Microphone -> AudioService -> RNNoise -> VADHandler: noise
        # suppression runs on the raw, full-native-rate chunk (before
        # resampling to 16kHz), since RNNoise's model is specifically
        # trained at 48kHz and denoising after downsampling would both
        # violate that and throw away exactly the high-frequency
        # information the model uses. process() is a no-op passthrough
        # (returns raw_native_rate_int16 unchanged) when noise
        # suppression is disabled/unavailable/failing, so everything
        # below is completely unaffected either way -- this is the
        # *only* call site for noise suppression in the entire pipeline.
        denoised_native_rate_int16 = (
            self._noise_suppressor.process(raw_native_rate_int16, native_rate)
            if self._noise_suppressor is not None
            else raw_native_rate_int16
        )

        frame_16k = resample_int16(denoised_native_rate_int16, native_rate, VAD_SAMPLE_RATE)

        if frame_16k.size == 0:
            # Should be unreachable given the length guard above (see its
            # docstring), but checked explicitly since this is exactly
            # the condition that must never reach VAD/Whisper.
            logger.warning(
                "AUDIO_CHUNK_DIAGNOSTIC: resample_int16() produced an empty frame from a %d-sample raw "
                "chunk (native_rate=%dHz); skipping",
                len(raw_native_rate_int16),
                native_rate,
            )
            return

        frame_bytes = frame_16k.astype(np.int16).tobytes()

        with self._chunk_lock:
            self._latest_audio_chunk = frame_bytes

        # VAD self-gates on current_state (only acts during PLAYING_AUDIO,
        # and continues an already-started INTERRUPTED silence-wait), so
        # it is safe and correct to always forward every frame to it.
        self._vad.process_frame(frame_bytes)

        # Computed once here (rather than separately inside
        # _accumulate_utterance()) so it can also gate the temporary
        # gain-diagnostic log below without a second VAD call.
        is_speech = self._vad.is_speech(frame_bytes)

        if is_speech:
            # TEMPORARY DIAGNOSTIC (investigating low captured amplitude /
            # garbage transcriptions): confirms whether attenuation, if
            # any, happens during capture (mic/device gain) or during our
            # own resampling -- logged only on speech frames to avoid
            # spamming every idle 30ms frame.
            raw_rms = _int16_rms(raw_native_rate_int16)
            resampled_rms = _int16_rms(frame_16k)
            logger.info(
                "AUDIO_GAIN_DIAGNOSTIC: raw_rms=%.4f (native %dHz, %d samples, int16 scale) -> "
                "resampled_rms=%.4f (16kHz, %d samples, int16 scale) [full scale=32768]",
                raw_rms,
                native_rate,
                len(raw_native_rate_int16),
                resampled_rms,
                len(frame_16k),
            )

        current_state = self._state.current_state
        if current_state == WAITING_FOR_WAKE_WORD:
            self._state.set_wake_word_status("listening")
            self._accumulate_utterance(frame_bytes, frame_16k, is_speech, self._finish_wake_word_utterance)
        elif current_state == CONVERSATION_ACTIVE:
            self._state.set_wake_word_status("inactive")
            self._accumulate_utterance(frame_bytes, frame_16k, is_speech, self._finish_conversation_utterance)
        else:
            self._state.set_wake_word_status("inactive")
            if self._utterance_active:
                # State changed mid-utterance (e.g. a face was lost);
                # abandon it rather than let it keep growing unseen.
                logger.debug("Abandoning in-progress utterance: state changed to %s", current_state)
                self._reset_utterance()

    def _accumulate_utterance(
        self, frame_bytes: bytes, frame_16k: np.ndarray, is_speech: bool, on_complete: Callable[[np.ndarray], None]
    ) -> None:
        """Accumulate frames from speech onset to trailing silence (or a hard cap), then hand off.

        The buffer built here is strictly bounded by
        max_utterance_seconds (self._max_utterance_frames) and is
        cleared the instant an utterance completes, regardless of
        outcome -- it never accumulates across utterances.

        Args:
            is_speech: Whether frame_bytes was VAD-flagged as speech,
                computed once by the caller (process_chunk()) rather
                than recomputed here.
        """
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

            # Hard guard: reject an empty accumulated utterance gracefully
            # rather than handing it to Whisper (which has been observed
            # to crash with "RuntimeError: cannot reshape tensor of 0
            # elements into shape [1, 0, 8, -1]" on it). Given the
            # malformed-chunk guard in process_chunk() above (no
            # zero-length frame_16k can enter self._utterance_chunks),
            # this should be unreachable in practice; it stays as a
            # second, source-level line of defense alongside
            # WhisperService._audio_rejection_reason()'s own empty-buffer
            # check, and its log records exactly how many frames were
            # accumulated, to help identify whether emptiness came from
            # zero-length frames or a genuinely empty frame list.
            if audio_int16.size == 0:
                logger.warning(
                    "Rejecting empty accumulated utterance before Whisper (accumulated %d frame(s), "
                    "concatenated length=0); not calling Whisper",
                    len(chunks),
                )
                return

            rms_before_normalization = _int16_rms(audio_int16)
            audio_float32 = (audio_int16.astype(np.float32) / 32768.0).clip(-1.0, 1.0)
            rms_after_normalization = float(np.sqrt(np.mean(np.square(audio_float32, dtype=np.float64))))

            # TEMPORARY DIAGNOSTIC: rms_after_normalization should equal
            # rms_before_normalization / 32768 almost exactly (int16 ->
            # [-1, 1] float32 is a pure linear scale, per resample_int16()
            # / the /32768.0 division just above -- neither step can
            # attenuate beyond that fixed ratio). If the captured
            # amplitude is already this low before normalization, the
            # cause is upstream (microphone gain / capture device), not
            # this conversion.
            logger.info(
                "AUDIO_NORMALIZATION_DIAGNOSTIC: utterance_samples=%d rms_before_normalization=%.4f "
                "(int16 scale) rms_after_normalization=%.6f (float32 [-1,1] scale) "
                "actual_ratio=%.8f expected_ratio=%.8f (1/32768)",
                len(audio_int16),
                rms_before_normalization,
                rms_after_normalization,
                (rms_after_normalization / rms_before_normalization) if rms_before_normalization else float("nan"),
                1.0 / 32768.0,
            )

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
