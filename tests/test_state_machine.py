"""Unit tests for the validated finite state machine (STATE_MACHINE.md).

Run with: python -m unittest discover tests
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.state_manager import AppState, VALID_TRANSITIONS


def _fresh_state() -> AppState:
    return AppState(config={
        "whisper_model": "medium", "face_confidence": 0.6, "vad_aggressiveness": 2,
        "conversation_timeout": 30, "wake_words": {},
    })


class TestValidTransitions(unittest.TestCase):
    def test_full_happy_path(self) -> None:
        state = _fresh_state()
        path = [
            "FACE_DETECTED", "FACE_RECOGNIZED", "GREETING", "WAITING_FOR_WAKE_WORD",
            "LANGUAGE_SELECTION", "CONVERSATION_ACTIVE", "PLAYING_AUDIO", "INTERRUPTED",
            "PLAYING_AUDIO", "CONVERSATION_ACTIVE", "TIMEOUT", "RETURN_TO_IDLE", "IDLE",
        ]
        for target in path:
            self.assertTrue(state.set_state(target), f"expected {target} to be accepted")
            self.assertEqual(state.current_state, target)

    def test_self_transition_is_always_a_noop_confirmation(self) -> None:
        state = _fresh_state()
        self.assertTrue(state.set_state("IDLE"))
        self.assertEqual(state.current_state, "IDLE")

    def test_every_diagram_edge_is_individually_accepted(self) -> None:
        for source, targets in VALID_TRANSITIONS.items():
            for target in targets:
                state = _fresh_state()
                state.current_state = source  # jump directly, bypassing validation, for isolation
                self.assertTrue(
                    state.set_state(target),
                    f"{source} -> {target} should be a valid transition",
                )


class TestInvalidTransitionsRejected(unittest.TestCase):
    def test_idle_to_playing_audio_rejected(self) -> None:
        # STATE_MACHINE.md's own cited invalid example.
        state = _fresh_state()
        self.assertFalse(state.set_state("PLAYING_AUDIO"))
        self.assertEqual(state.current_state, "IDLE")

    def test_greeting_to_timeout_rejected(self) -> None:
        # STATE_MACHINE.md's own cited invalid example.
        state = _fresh_state()
        state.current_state = "GREETING"
        self.assertFalse(state.set_state("TIMEOUT"))
        self.assertEqual(state.current_state, "GREETING")

    def test_unknown_state_name_rejected(self) -> None:
        state = _fresh_state()
        self.assertFalse(state.set_state("NOT_A_REAL_STATE"))
        self.assertEqual(state.current_state, "IDLE")

    def test_skipping_states_rejected(self) -> None:
        state = _fresh_state()
        # IDLE -> LANGUAGE_SELECTION skips FACE_DETECTED/FACE_RECOGNIZED/GREETING/WAITING_FOR_WAKE_WORD
        self.assertFalse(state.set_state("LANGUAGE_SELECTION"))
        self.assertEqual(state.current_state, "IDLE")

    def test_rejected_transition_does_not_change_state(self) -> None:
        state = _fresh_state()
        state.current_state = "CONVERSATION_ACTIVE"
        state.set_state("IDLE")  # not a valid edge from CONVERSATION_ACTIVE
        self.assertEqual(state.current_state, "CONVERSATION_ACTIVE")


class TestStatusFields(unittest.TestCase):
    def test_set_status_updates_field(self) -> None:
        state = _fresh_state()
        state.set_status("camera_status", "ACTIVE")
        self.assertEqual(state.camera_status, "ACTIVE")

    def test_set_status_rejects_unknown_field(self) -> None:
        state = _fresh_state()
        with self.assertRaises(AttributeError):
            state.set_status("not_a_real_field", "value")

    def test_snapshot_reflects_current_values(self) -> None:
        state = _fresh_state()
        state.set_status("recognized_user", "natnael")
        snapshot = state.snapshot()
        self.assertEqual(snapshot["recognized_user"], "natnael")


if __name__ == "__main__":
    unittest.main()
