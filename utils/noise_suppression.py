"""RNNoise-based real-time microphone noise suppression for EthioChatbot V2.

Inserted immediately after raw microphone capture and before resampling,
per the desired pipeline:

    Microphone -> AudioService -> RNNoise -> VADHandler -> Wake Word Detection -> WhisperService

utils/audio_service.py's only interaction with this module is a single
call, NoiseSuppressor.process(frame, sample_rate) -- all RNNoise-specific
behavior (engine loading, frame-size handling, sample-rate conversion,
failure recovery) is encapsulated here, per the constraint that RNNoise
logic must not be spread throughout the system. utils/vad_handler.py,
utils/whisper_utils.py, utils/fsm.py, and every event name/FSM transition
are completely untouched by this module: it produces a same-length,
same-rate int16 frame, so everything downstream of AudioService.process_chunk()
continues to operate exactly as before, unaware noise suppression exists.

Engine: RNNoise (https://github.com/xiph/rnnoise), a small recurrent
neural network specifically designed for real-time noise suppression on
resource-constrained hardware (originally built for WebRTC), making it
well suited to this project's Raspberry Pi 4 deployment target. Accessed
via the `pyrnnoise` PyPI package's bundled compiled librnnoise.so (which
ships prebuilt wheels for linux_aarch64, i.e. Raspberry Pi OS 64-bit).

Why this module bypasses pyrnnoise's own top-level API: pyrnnoise's
package __init__.py unconditionally imports `audiolab` (for CLI/file
-processing features this project never uses), and in practice that
import chain is broken in this environment (ModuleNotFoundError: No
module named 'av.option', a version mismatch between audiolab and its
own `av` dependency) and, even when it does import cleanly, pulls in
~90MB of unrelated dependencies (matplotlib, PyAV/ffmpeg bindings,
soundfile) -- unnecessary weight for a Raspberry Pi deployment. The
actual RNNoise binding needed here (pyrnnoise/rnnoise.py: a small,
dependency-free ctypes wrapper around the bundled compiled library) has
none of that baggage, so it is loaded directly by file path via
importlib, skipping pyrnnoise/__init__.py entirely. See
_load_rnnoise_backend().
"""
from __future__ import annotations

import importlib.util
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np

from utils.logger import get_logger

logger = get_logger(__name__)

RNNOISE_SAMPLE_RATE = 48000

# Diagnostics run on every ~10-30ms frame; without rate-limiting,
# NOISE_SUPPRESSION_STATS would produce 30-100 log lines per second.
_MIN_STATS_LOG_INTERVAL_SECONDS = 2.0

# Mirrors utils/audio_service.py's own read-failure-recovery threshold:
# a handful of bad frames is tolerated (fall back to the original audio
# for each), but sustained failure means the engine itself is broken, so
# suppression is disabled for the rest of the session rather than
# retrying forever on every single frame.
_MAX_CONSECUTIVE_FAILURES = 10


class NoiseSuppressionError(Exception):
    """Raised when the configured noise suppression engine cannot be loaded."""


def _load_rnnoise_backend():
    """Load pyrnnoise's low-level ctypes bindings, bypassing pyrnnoise/__init__.py.

    See module docstring for why. Uses importlib.util.find_spec() (which
    locates a package without importing/executing it) to find pyrnnoise's
    install directory, then loads rnnoise.py from that directory as a
    standalone module by file path.

    Returns:
        The loaded rnnoise backend module, exposing create(), destroy(),
        process_mono_frame(state, frame), FRAME_SIZE (480), and
        SAMPLE_RATE (48000).

    Raises:
        NoiseSuppressionError: if pyrnnoise is not installed, its bundled
            backend/library is missing, or it fails to load.
    """
    spec = importlib.util.find_spec("pyrnnoise")
    if spec is None or not spec.submodule_search_locations:
        raise NoiseSuppressionError("pyrnnoise is not installed (pip install pyrnnoise)")

    package_dir = Path(list(spec.submodule_search_locations)[0])
    backend_path = package_dir / "rnnoise.py"
    if not backend_path.exists():
        raise NoiseSuppressionError(f"pyrnnoise's rnnoise.py backend is missing: {backend_path}")

    backend_spec = importlib.util.spec_from_file_location("_ethiochatbot_rnnoise_backend", backend_path)
    if backend_spec is None or backend_spec.loader is None:
        raise NoiseSuppressionError(f"Could not build an import spec for {backend_path}")

    backend = importlib.util.module_from_spec(backend_spec)
    try:
        backend_spec.loader.exec_module(backend)
    except Exception as exc:
        raise NoiseSuppressionError(f"Failed to load RNNoise backend from {backend_path}: {exc}") from exc

    return backend


def _rms(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))


def _resample_int16(samples: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
    """Linear-interpolation resample, self-contained.

    Deliberately duplicates utils/audio_service.py's resample_int16()
    (same technique) rather than importing it: that module will need to
    import this one to call process(), so importing back would be
    circular, and per this module's encapsulation requirement, RNNoise's
    sample-rate handling belongs entirely here regardless.
    """
    if from_rate == to_rate or len(samples) == 0:
        return samples.astype(np.int16)

    duration = len(samples) / from_rate
    target_length = max(0, int(round(duration * to_rate)))
    if target_length == 0:
        return np.array([], dtype=np.int16)

    original_times = np.linspace(0, duration, num=len(samples), endpoint=False)
    target_times = np.linspace(0, duration, num=target_length, endpoint=False)
    resampled = np.interp(target_times, original_times, samples.astype(np.float64))
    return resampled.astype(np.int16)


def _fit_length(audio: np.ndarray, target_length: int) -> np.ndarray:
    """Pad or truncate to exactly target_length samples.

    Guards against sub-sample rounding drift from a resample-up-then-
    resample-down round trip (used when the capture device's native rate
    isn't already 48kHz) -- downstream consumers (WebRTC VAD's fixed
    frame-size requirement, latest_audio_chunk) rely on the processed
    frame being exactly the same length as the frame that was captured.
    """
    if len(audio) == target_length:
        return audio
    if len(audio) > target_length:
        return audio[:target_length]
    return np.pad(audio, (0, target_length - len(audio)))


class NoiseSuppressor:
    """Real-time RNNoise noise suppression for one continuous capture stream.

    Implements app.py's Service protocol (name, start, stop): RNNoise's
    native (C-level) denoising state is created in start() and destroyed
    in stop(), matching its lifecycle -- utils/audio_service.py's
    AudioService owns exactly one instance for the life of a capture
    session, mirroring how it owns exactly one VADHandler/WhisperService.

    process() never raises and never returns an empty/NaN/Inf/wrong-
    length buffer: on any failure (engine not initialized, disabled by
    config, an unsupported engine name, or an error from the native
    library) it logs and returns the original input frame unchanged, so
    a broken or absent RNNoise installation degrades gracefully to
    exactly today's behavior rather than breaking capture.
    """

    name = "noise_suppressor"

    def __init__(self, enabled: bool = True, engine: str = "rnnoise") -> None:
        """Args:
            enabled: config/settings.json's noise_suppression_enabled.
                False (or an unsupported engine) is a fully valid,
                supported configuration: process() then always returns
                its input unchanged, i.e. today's AudioService behavior.
            engine: config/settings.json's noise_suppression_engine.
                Only "rnnoise" is implemented; any other value disables
                suppression (logged) rather than raising, so an unknown
                future value degrades safely instead of crashing startup.
        """
        self._configured_enabled = enabled
        self._engine_name = engine
        self._backend = None
        self._state = None
        self._active = False
        self._consecutive_failures = 0
        self._last_stats_log = 0.0
        self._lock = threading.Lock()

    @property
    def is_active(self) -> bool:
        """Whether RNNoise is actually running (config-enabled AND successfully initialized)."""
        return self._active

    def start(self) -> None:
        """Initialize the RNNoise engine, if configured and available.

        Never raises: any failure to load/initialize RNNoise is logged
        and leaves this suppressor inactive (process() then passes
        audio through unchanged), so a missing/broken dependency cannot
        prevent the rest of the application from starting.
        """
        if not self._configured_enabled:
            logger.info("NOISE_SUPPRESSION_ENABLED: false (disabled via config/settings.json)")
            logger.info("AUDIO_PATH: raw -> vad -> whisper")
            return

        if self._engine_name != "rnnoise":
            logger.warning(
                "Unsupported noise_suppression_engine=%r (only 'rnnoise' is implemented); "
                "noise suppression disabled",
                self._engine_name,
            )
            logger.info("NOISE_SUPPRESSION_ENABLED: false (unsupported engine=%r)", self._engine_name)
            logger.info("AUDIO_PATH: raw -> vad -> whisper")
            return

        try:
            self._backend = _load_rnnoise_backend()
            self._state = self._backend.create()
            self._active = True
            logger.info(
                "NOISE_SUPPRESSION_ENABLED: true (engine=rnnoise, frame_size=%d samples, sample_rate=%dHz)",
                self._backend.FRAME_SIZE,
                self._backend.SAMPLE_RATE,
            )
            logger.info("AUDIO_PATH: raw -> rnnoise -> vad -> whisper")
        except NoiseSuppressionError as exc:
            logger.warning("Noise suppression could not be initialized (%s); continuing without it", exc)
            logger.info("NOISE_SUPPRESSION_ENABLED: false (initialization failed: %s)", exc)
            logger.info("AUDIO_PATH: raw -> vad -> whisper")
            self._backend = None
            self._state = None
            self._active = False

    def stop(self) -> None:
        """Release the native RNNoise state, if one was created."""
        if self._state is not None and self._backend is not None:
            try:
                self._backend.destroy(self._state)
            except Exception:
                logger.exception("Error destroying RNNoise state")
        self._state = None
        self._backend = None
        self._active = False
        logger.info("Noise suppressor stopped")

    def process(self, frame: np.ndarray, sample_rate: int) -> np.ndarray:
        """Denoise one captured audio frame.

        Args:
            frame: Mono int16 PCM samples, any length, captured at
                sample_rate.
            sample_rate: The native rate `frame` was captured at.
                RNNoise's model requires exactly 48kHz; a frame at a
                different rate is transparently resampled up before
                processing and back down afterward (this module's
                sample-rate handling, not the caller's concern).

        Returns:
            A denoised frame at the same length and sample_rate as the
            input. If noise suppression is disabled, not initialized,
            or the engine fails on this specific frame, returns `frame`
            unchanged instead -- this method never raises.
        """
        if not self._active or frame.size == 0:
            return frame

        try:
            return self._process_unsafe(frame, sample_rate)
        except Exception:
            self._consecutive_failures += 1
            logger.exception(
                "RNNoise processing failed (failure %d/%d); falling back to original audio for this frame",
                self._consecutive_failures,
                _MAX_CONSECUTIVE_FAILURES,
            )
            if self._consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                logger.warning(
                    "%d consecutive RNNoise failures; disabling noise suppression for the "
                    "remainder of this session (falling back to raw audio)",
                    self._consecutive_failures,
                )
                self._active = False
            return frame

    def _process_unsafe(self, frame: np.ndarray, sample_rate: int) -> np.ndarray:
        """The actual RNNoise call chain; exceptions propagate to process()'s guard."""
        original_length = len(frame)
        needs_resample = sample_rate != RNNOISE_SAMPLE_RATE
        frame_48k = _resample_int16(frame, sample_rate, RNNOISE_SAMPLE_RATE) if needs_resample else frame

        input_rms = _rms(frame_48k)

        frame_size = self._backend.FRAME_SIZE
        denoised_chunks = []
        with self._lock:
            for start in range(0, len(frame_48k), frame_size):
                sub_frame = frame_48k[start : start + frame_size]
                denoised_sub, _speech_prob = self._backend.process_mono_frame(self._state, sub_frame)
                denoised_chunks.append(denoised_sub)
        denoised_48k = np.concatenate(denoised_chunks) if denoised_chunks else np.array([], dtype=np.int16)

        if not self._is_valid_output(denoised_48k):
            logger.warning("RNNoise returned invalid output (empty/NaN/Inf); falling back to original audio")
            self._consecutive_failures += 1
            return frame

        self._consecutive_failures = 0
        output_rms = _rms(denoised_48k)
        self._maybe_log_stats(input_rms, output_rms)

        denoised = _resample_int16(denoised_48k, RNNOISE_SAMPLE_RATE, sample_rate) if needs_resample else denoised_48k
        return _fit_length(denoised, original_length)

    @staticmethod
    def _is_valid_output(audio: np.ndarray) -> bool:
        if audio.size == 0:
            return False
        if np.isnan(audio).any() or np.isinf(audio).any():
            return False
        return True

    def _maybe_log_stats(self, input_rms: float, output_rms: float) -> None:
        now = time.time()
        if now - self._last_stats_log < _MIN_STATS_LOG_INTERVAL_SECONDS:
            return
        self._last_stats_log = now
        suppression_ratio = (1.0 - (output_rms / input_rms)) if input_rms > 0 else 0.0
        logger.info(
            "NOISE_SUPPRESSION_STATS: input_rms=%.2f output_rms=%.2f suppression_ratio=%.4f",
            input_rms,
            output_rms,
            suppression_ratio,
        )
