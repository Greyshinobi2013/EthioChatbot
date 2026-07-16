"""Unit tests for the scenario engine (SCENARIOS.md).

Uses isolated temp fixtures rather than the real audio/config/dialog_config.json
so this suite never depends on, or mutates, live project data.

Run with: python -m unittest discover tests
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.conversation_manager import (
    ScenarioError,
    load_scenarios,
    load_scenarios_raw,
    match_scenario,
    resolve_response_audio,
    save_scenarios,
)


def _write_silent_wav(path: Path, seconds: float = 0.2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * int(16000 * seconds))


class ScenarioTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.dialog_path = self.root / "dialog_config.json"

        _write_silent_wav(self.root / "audio" / "english" / "name.wav")
        _write_silent_wav(self.root / "audio" / "english" / "greeting.wav")
        _write_silent_wav(self.root / "audio" / "english" / "unknown_question.wav")

        data = {
            "english": [
                {"user_text": "what is your name", "response_audio": str(self.root / "audio/english/name.wav")},
                {"user_text": "hello", "response_audio": str(self.root / "audio/english/greeting.wav")},
            ],
            "amharic": [],
            "arabic": [],
        }
        self.dialog_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()


class TestLoadScenarios(ScenarioTestCase):
    def test_loads_valid_entries(self) -> None:
        scenarios = load_scenarios(self.dialog_path)
        self.assertEqual(len(scenarios["english"]), 2)
        self.assertEqual(scenarios["amharic"], [])

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(ScenarioError):
            load_scenarios(self.root / "does_not_exist.json")

    def test_malformed_json_raises(self) -> None:
        bad = self.root / "bad.json"
        bad.write_text("{not valid json", encoding="utf-8")
        with self.assertRaises(ScenarioError):
            load_scenarios(bad)

    def test_entry_missing_fields_is_skipped_not_fatal(self) -> None:
        mixed = self.root / "mixed.json"
        mixed.write_text(json.dumps({"english": [
            {"user_text": "no audio field"},
            {"response_audio": "no text field"},
        ]}), encoding="utf-8")
        scenarios = load_scenarios(mixed)
        self.assertEqual(scenarios["english"], [])

    def test_missing_audio_file_is_skipped_not_fatal(self) -> None:
        missing = self.root / "missing_audio.json"
        missing.write_text(json.dumps({"english": [
            {"user_text": "ghost", "response_audio": str(self.root / "audio/english/does_not_exist.wav")},
        ]}), encoding="utf-8")
        scenarios = load_scenarios(missing)
        self.assertEqual(scenarios["english"], [])

    def test_raw_load_keeps_invalid_entries_for_editing(self) -> None:
        mixed = self.root / "mixed2.json"
        mixed.write_text(json.dumps({"english": [{"user_text": "no audio field"}]}), encoding="utf-8")
        raw = load_scenarios_raw(mixed)
        self.assertEqual(len(raw["english"]), 1)


class TestMatchScenario(ScenarioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.scenarios = load_scenarios(self.dialog_path)

    def test_exact_match(self) -> None:
        match = match_scenario("what is your name", "english", self.scenarios)
        self.assertIsNotNone(match)
        self.assertTrue(match["response_audio"].endswith("name.wav"))

    def test_exact_match_normalizes_case_and_punctuation(self) -> None:
        match = match_scenario("What Is Your Name?!", "english", self.scenarios)
        self.assertIsNotNone(match)
        self.assertTrue(match["response_audio"].endswith("name.wav"))

    def test_keyword_match_paraphrase(self) -> None:
        match = match_scenario("hey, tell me your name please", "english", self.scenarios)
        self.assertIsNotNone(match)
        self.assertTrue(match["response_audio"].endswith("name.wav"))

    def test_keyword_match_does_not_false_positive_on_stopwords(self) -> None:
        # "what is the weather" shares only "what"/"is" with "what is your
        # name" -- both are stopwords, so this must NOT match (regression
        # test for the bug found and fixed in Milestone 4).
        match = match_scenario("what is the weather like today", "english", self.scenarios)
        self.assertIsNone(match)

    def test_no_match_returns_none(self) -> None:
        match = match_scenario("completely unrelated text", "english", self.scenarios)
        self.assertIsNone(match)

    def test_language_scoping(self) -> None:
        # English text must not match against a language with no scenarios.
        match = match_scenario("what is your name", "amharic", self.scenarios)
        self.assertIsNone(match)

    def test_empty_text_returns_none(self) -> None:
        self.assertIsNone(match_scenario("", "english", self.scenarios))


class TestFallback(ScenarioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.scenarios = load_scenarios(self.dialog_path)

    def test_fallback_used_when_no_match(self) -> None:
        path = resolve_response_audio("tell me a joke", "english", self.scenarios)
        self.assertEqual(path.name, "unknown_question.wav")

    def test_fallback_used_for_language_with_no_scenarios(self) -> None:
        path = resolve_response_audio("ሰላም", "amharic", self.scenarios)
        self.assertTrue(str(path).endswith("amharic/unknown_question.wav"))

    def test_matched_scenario_not_fallback(self) -> None:
        path = resolve_response_audio("what is your name", "english", self.scenarios)
        self.assertEqual(path.name, "name.wav")


class TestSaveScenarios(ScenarioTestCase):
    def test_round_trip(self) -> None:
        scenarios = load_scenarios_raw(self.dialog_path)
        scenarios["english"].append({"user_text": "goodbye", "response_audio": "goodbye.wav"})
        save_scenarios(scenarios, self.dialog_path)

        reloaded = load_scenarios_raw(self.dialog_path)
        self.assertEqual(len(reloaded["english"]), 3)
        self.assertEqual(reloaded["english"][-1]["user_text"], "goodbye")


if __name__ == "__main__":
    unittest.main()
