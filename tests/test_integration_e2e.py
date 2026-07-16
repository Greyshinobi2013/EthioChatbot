"""Integration test: full event-driven conversation flow.

camera_service/audio_service are not started here (no hardware dependency,
so this runs anywhere, including CI). FACE_RECOGNIZED, WAKE_WORD_DETECTED,
and TRANSCRIPTION_READY are published directly through the real event bus
-- exactly as camera_service/audio_service do in production -- to drive
the real conversation_manager, state_manager (validated FSM), scenario
engine, and playback code deterministically.

This intentionally exercises the REAL project dialog_config.json ("what is
your name" -> name.wav must be present) since this is an integration test
of the shipped configuration, not an isolated unit test.

Interruption (VAD) is not covered here since it requires a real
microphone stream -- see the live-hardware verification in the Milestone 8
integration report instead.

Run with: python -m unittest discover tests
"""
from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import conversation_manager
from utils.event_bus import publish
from utils.state_manager import AppState, load_configuration


class TestEndToEndConversationFlow(unittest.TestCase):
    def test_full_workflow(self) -> None:
        config = load_configuration()
        config = dict(config)
        config["conversation_timeout"] = 3  # short, so this test finishes quickly

        state = AppState(config=config)
        conversation_manager.register_handlers(state)

        stop_event = threading.Event()
        timeout_thread = threading.Thread(
            target=conversation_manager.monitor_timeout, args=(state, stop_event), daemon=True
        )
        timeout_thread.start()

        try:
            # Face Detected -> Face Recognized -> Greeting -> Waiting for wake word
            publish("FACE_DETECTED")
            self._wait_for_state(state, "FACE_DETECTED")

            publish("FACE_RECOGNIZED", user_id="integration_test_user", confidence=0.99)
            self._wait_for_state(state, "WAITING_FOR_WAKE_WORD", timeout=10)

            # Wake Word -> Language Selection -> Conversation Activation
            publish("WAKE_WORD_DETECTED", language="english", phrase="hello robot", text="hello robot")
            self._wait_for_state(state, "CONVERSATION_ACTIVE")
            self.assertEqual(state.current_language, "english")

            # Whisper (simulated) -> Scenario Matching -> Audio Playback
            publish("TRANSCRIPTION_READY", text="what is your name", language="en")
            self._wait_for_state(state, "PLAYING_AUDIO", timeout=5)
            self._wait_for_state(state, "CONVERSATION_ACTIVE", timeout=10)

            # Timeout -> Return To Idle
            self._wait_for_state(state, "IDLE", timeout=8)
            self.assertIsNone(state.current_language)
            self.assertIsNone(state.recognized_user)
        finally:
            stop_event.set()
            timeout_thread.join(timeout=5)

    def _wait_for_state(self, state: AppState, expected: str, timeout: float = 5) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if state.current_state == expected:
                return
            time.sleep(0.05)
        self.fail(f"Timed out waiting for state {expected!r}; still at {state.current_state!r}")


if __name__ == "__main__":
    unittest.main()
