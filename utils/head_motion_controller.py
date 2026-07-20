"""Robotic neck (yaw + pitch servo) control for EthioChatbot V3.

Per HEAD_MOTION_SPECIFICATION_V3.md and SYSTEM_ARCHITECTURE_V3.md's Head
Motion Controller component: this module owns the two neck servos and
nothing else (DEVELOPMENT_RULES_V3.md Rule 35 -- servo control is its
sole responsibility). It performs no face detection, recognition, FSM
transition, or audio playback of its own:

- utils/camera_service.py feeds it live face positions every frame via
  track_face().
- This controller subscribes to STATE_CHANGED itself (mirroring
  utils/greeting_manager.py's own subscription pattern) to switch
  between surveillance scanning and face tracking, and to keep pitch
  neutral outside of greetings, per STATE_MACHINE_V3.md's Head Motion
  State Summary table. fsm.py itself never calls into this module
  directly (STATE_MACHINE_V3.md: "The FSM shall never perform servo
  control").
- utils/greeting_manager.py calls greet_nod() once per queued greeting.
- pages/1_Dashboard.py calls center_head() for the operator control and
  reads status via StateManager.get_head_motion_status().

Hardware access goes through gpiozero's AngularServo when available.
Raspberry Pi is the only officially supported target, but this dev
machine (and any environment without a wired servo) has no GPIO pin
factory available -- per DEVELOPMENT_RULES_V3.md's error handling rule
("Servo Failure" must be logged, never crash the system), _Servo falls
back to a simulated, in-memory-only mode automatically whenever
hardware initialization fails, exactly like utils/camera_service.py's
graceful handling of camera failures.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

from utils.event_bus import Event, EventBus
from utils.fsm import (
    FACE_DETECTION_MODE,
    PLAY_GREETINGS,
)
from utils.logger import get_logger
from utils.state_manager import StateManager

logger = get_logger(__name__)

YAW_CENTER_ANGLE = 90.0
YAW_LEFT_ANGLE = 45.0
YAW_RIGHT_ANGLE = 135.0

PITCH_CENTER_ANGLE = 90.0
PITCH_DOWN_ANGLE = 110.0

DEFAULT_YAW_PIN = 17
DEFAULT_PITCH_PIN = 27

# Dwell time at each surveillance-scan waypoint, and at each nod
# keyframe, in seconds. Kept as simple fixed constants per
# DEVELOPMENT_RULES_V3.md's simplicity-over-complexity preference --
# real physical servos take a fraction of a second to slew this range,
# so these dwell times give smooth, observable motion without needing
# a motion-profile/easing system.
SCAN_STEP_SECONDS = 1.0
NOD_STEP_SECONDS = 0.25

# Per-update yaw correction cap for track_face(), so a face that jumps
# far from center (e.g. a new track) turns toward smoothly instead of
# snapping instantly.
TRACK_MAX_STEP_DEGREES = 8.0


class _Servo:
    """One physical servo, or a logged software simulation if hardware is unavailable."""

    def __init__(self, pin: int, center_angle: float, name: str) -> None:
        self._name = name
        self._angle = center_angle
        self._device = None
        try:
            from gpiozero import AngularServo  # Raspberry-Pi-only dependency

            self._device = AngularServo(pin, min_angle=0, max_angle=180, initial_angle=center_angle)
            logger.info("%s servo initialized on GPIO pin %d", name, pin)
        except Exception as exc:
            logger.warning(
                "%s servo hardware unavailable (pin %d): %s -- running in simulated mode",
                name,
                pin,
                exc,
            )

    @property
    def is_hardware(self) -> bool:
        """Whether this servo is backed by real GPIO hardware."""
        return self._device is not None

    @property
    def angle(self) -> float:
        """The servo's last commanded angle, in degrees (0-180)."""
        return self._angle

    def set_angle(self, angle: float) -> None:
        """Move to angle (degrees, 0-180), logging and falling back to simulation on failure."""
        self._angle = angle
        if self._device is None:
            return
        try:
            self._device.angle = angle
        except Exception:
            logger.exception(
                "%s servo failed to move to %.1f degrees; continuing in simulated mode", self._name, angle
            )
            self._device = None

    def close(self) -> None:
        """Release the underlying GPIO device, if any."""
        if self._device is not None:
            try:
                self._device.close()
            except Exception:
                logger.exception("Error closing %s servo", self._name)
            self._device = None


class HeadMotionController:
    """Drives the yaw and pitch servos per HEAD_MOTION_SPECIFICATION_V3.md.

    Implements app.py's Service protocol (name, start, stop).
    """

    name = "head_motion_controller"

    def __init__(
        self,
        event_bus: EventBus,
        state_manager: StateManager,
        yaw_pin: int = DEFAULT_YAW_PIN,
        pitch_pin: int = DEFAULT_PITCH_PIN,
    ) -> None:
        """Args:
            event_bus: Bus this controller subscribes to (STATE_CHANGED)
                to switch between surveillance scanning and face
                tracking, and to keep pitch neutral outside greetings.
            state_manager: Shared state this controller publishes its
                yaw/pitch angle and servo status into, for the
                dashboard's Servo Status display.
            yaw_pin: GPIO pin the yaw (horizontal) servo is wired to.
            pitch_pin: GPIO pin the pitch (vertical) servo is wired to.
        """
        self._bus = event_bus
        self._state = state_manager
        self._yaw = _Servo(yaw_pin, YAW_CENTER_ANGLE, "yaw")
        self._pitch = _Servo(pitch_pin, PITCH_CENTER_ANGLE, "pitch")

        self._scan_lock = threading.Lock()
        self._scanning = False
        self._scan_thread: Optional[threading.Thread] = None
        self._scan_stop = threading.Event()

        self._publish_status()
        self._bus.subscribe("STATE_CHANGED", self._on_state_changed)

    # -- Service protocol --------------------------------------------------

    def start(self) -> None:
        """Center both servos on startup, then start scanning if already in FACE_DETECTION_MODE.

        fsm.py never publishes STATE_CHANGED for the state the system
        boots into (only for actual transitions), so without this
        check a fresh startup would sit in FACE_DETECTION_MODE
        forever without ever starting the surveillance scan.
        """
        self.center_head()
        if self._state.current_state == FACE_DETECTION_MODE:
            self.start_scan()
        logger.info("Head motion controller started")

    def stop(self) -> None:
        """Stop scanning and release servo hardware."""
        self.stop_scan()
        self._yaw.close()
        self._pitch.close()
        logger.info("Head motion controller stopped")

    # -- FSM-driven mode switching -------------------------------------------

    def _on_state_changed(self, event: Event) -> None:
        """Switch yaw between surveillance scanning and face tracking.

        Per STATE_MACHINE_V3.md's Head Motion State Summary table:
        yaw scans only in FACE_DETECTION_MODE and tracks faces in
        every other state (track_face() calls from
        utils/camera_service.py do the actual turning); pitch stays
        neutral everywhere except PLAY_GREETINGS, where
        utils/greeting_manager.py drives it explicitly via
        greet_nod() -- so this handler leaves pitch alone there rather
        than fighting an in-progress nod.
        """
        to_state = event.payload.get("to")
        if to_state == FACE_DETECTION_MODE:
            self._set_pitch(PITCH_CENTER_ANGLE)
            self.start_scan()
        else:
            self.stop_scan()
            if to_state != PLAY_GREETINGS:
                self._set_pitch(PITCH_CENTER_ANGLE)

    # -- Yaw: surveillance scanning -------------------------------------------

    def start_scan(self) -> None:
        """Begin continuous Left-Center-Right-Center yaw surveillance scanning."""
        with self._scan_lock:
            if self._scanning:
                return
            self._scanning = True
            self._scan_stop.clear()
            self._scan_thread = threading.Thread(target=self._run_scan, name="HeadScan", daemon=True)
            self._scan_thread.start()
        logger.info("Yaw surveillance scan started")

    def stop_scan(self) -> None:
        """Stop surveillance scanning, if active."""
        with self._scan_lock:
            if not self._scanning:
                return
            self._scanning = False
            self._scan_stop.set()
            thread = self._scan_thread
            self._scan_thread = None
        if thread is not None:
            thread.join(timeout=2.0)
        logger.info("Yaw surveillance scan stopped")

    def _run_scan(self) -> None:
        pattern = (YAW_LEFT_ANGLE, YAW_CENTER_ANGLE, YAW_RIGHT_ANGLE, YAW_CENTER_ANGLE)
        index = 0
        while not self._scan_stop.is_set():
            self._set_yaw(pattern[index % len(pattern)])
            index += 1
            self._scan_stop.wait(SCAN_STEP_SECONDS)

    # -- Yaw: face tracking ---------------------------------------------------

    def track_face(self, face_position: Optional[float]) -> None:
        """Turn the yaw servo toward a visible user.

        Ignored while a surveillance scan is active, so per-frame
        tracking calls from utils/camera_service.py never fight the
        scan pattern -- utils/fsm.py's STATE_CHANGED events are what
        stop scanning once a face is detected.

        Args:
            face_position: Normalized horizontal offset of the target
                face from the camera's center, in [-1.0, 1.0]
                (negative = left of center, positive = right). None if
                no user is currently visible to track -- the yaw servo
                holds its last position.
        """
        if face_position is None or self._scanning:
            return
        face_position = max(-1.0, min(1.0, face_position))
        target = YAW_CENTER_ANGLE + face_position * (YAW_RIGHT_ANGLE - YAW_CENTER_ANGLE)
        current = self._yaw.angle
        step = max(-TRACK_MAX_STEP_DEGREES, min(TRACK_MAX_STEP_DEGREES, target - current))
        self._set_yaw(current + step)

    # -- Pitch: greeting nodding ------------------------------------------------

    def greet_nod(self) -> None:
        """Perform one Center-Down-Center-Down-Center pitch nod for a single greeting.

        Runs on its own background thread so it never blocks the
        greeting playback it accompanies -- utils/greeting_manager.py
        fires both at the same time and waits for neither.
        """
        threading.Thread(target=self._run_nod, name="HeadNod", daemon=True).start()

    def _run_nod(self) -> None:
        pattern = (PITCH_CENTER_ANGLE, PITCH_DOWN_ANGLE, PITCH_CENTER_ANGLE, PITCH_DOWN_ANGLE, PITCH_CENTER_ANGLE)
        for angle in pattern:
            self._set_pitch(angle)
            time.sleep(NOD_STEP_SECONDS)
        logger.info("Greeting nod sequence complete")

    # -- Servo centering ---------------------------------------------------

    def center_head(self) -> None:
        """Return both servos to their centered position (Dashboard's "Center Head" control).

        Stops surveillance scanning too -- otherwise the scan loop
        would immediately turn the head away from center again,
        making the operator's action appear to do nothing.
        """
        self.stop_scan()
        self._set_yaw(YAW_CENTER_ANGLE)
        self._set_pitch(PITCH_CENTER_ANGLE)
        logger.info("Head centered")

    # -- Shared status helpers -----------------------------------------------

    def _set_yaw(self, angle: float) -> None:
        self._yaw.set_angle(angle)
        self._publish_status()

    def _set_pitch(self, angle: float) -> None:
        self._pitch.set_angle(angle)
        self._publish_status()

    def _publish_status(self) -> None:
        hardware_ok = self._yaw.is_hardware and self._pitch.is_hardware
        self._state.set_head_motion_status(
            {
                "yaw_angle": self._yaw.angle,
                "pitch_angle": self._pitch.angle,
                "servo_status": "ok" if hardware_ok else "simulated",
            }
        )
