# Demonstration Readiness Report

Validated against `DEMO_SCRIPT.md`. **Status: READY.**

## Step-by-step readiness

| Step | Expected result | Status | Notes |
|---|---|---|---|
| 1. Launch Application | Starts, config loads, logging starts, webcam+mic init, FSM enters IDLE | ✅ READY | `streamlit run app.py`; ~1-2s to IDLE (excluding first-ever Whisper download) |
| 2. Enroll User Face | Face stored, appears in enrolled list | ✅ READY | Enroll Face page; webcam tab or upload tab |
| 3. Recognize User | Detected, recognized, name shown | ✅ READY | Live-verified repeatedly across the project |
| 4. Automatic Greeting | Plays without user action | ✅ READY | |
| 5. Wait For Wake Word | FSM enters WAITING_FOR_WAKE_WORD | ✅ READY | |
| 6. Speak Wake Word | Detected, event generated | ✅ READY | Configured phrases: "hello robot", "hey robot", "computer" (English); see `config/settings.json` for Amharic/Arabic phrases |
| 7. Language Selection | Language set, FSM enters CONVERSATION_ACTIVE | ✅ READY | Auto-inferred from which language's wake phrase matched |
| 8. Ask a Question | Transcribed, scenario matched | ✅ READY | English: "what is your name" / "hello" configured out of the box |
| 9. Play Response | Correct audio plays | ✅ READY | |
| 10. Interrupt Robot | VAD detects, pauses, plays "please wait" | ✅ READY | Speak clearly during playback |
| 11. Become Silent | Resumes from paused position | ✅ READY | ~1s of silence needed to trigger resume |
| 12. Wait For Timeout | FSM enters TIMEOUT | ✅ READY | Default 30s of no new question; configurable in Settings |
| 13. Return To Idle | Back to listening mode | ✅ READY | `recognized_user`/`current_language` cleared |

## Pre-demo checklist (run once before presenting)
1. `pip install -r requirements.txt` (includes `setuptools<81`, required for the VAD library).
2. Confirm `models/shape_predictor_68_face_landmarks.dat` and `models/dlib_face_recognition_resnet_model_v1.dat` are present (download once from `davisking/dlib-models` if missing — not needed again after that).
3. Run the app once **before** the demo so Whisper's `medium` model downloads and caches (~1.4GB, one-time; takes minutes on the first run, instant afterward).
4. Enroll the presenter's face via the Enroll Face page ahead of time.
5. `python -m unittest discover tests` — should show `OK`.

## Known risk and mitigation
**Whisper `medium` is slow on CPU-only hardware** (~24s to transcribe a 3-second clip on the machine this was built/tested on, no GPU). This affects wake-word responsiveness and question-answering latency, not correctness.
- **Mitigation**: switch to `base` or `small` in Settings before presenting on similar hardware — reduces the same transcription to ~2s with only a modest accuracy trade-off. Requires an app restart to take effect (settings don't hot-reload, disclosed on the Settings page itself).
- Both `medium` (spec default) and `base` (practical/fast) have been live-tested successfully; this is a latency tuning choice, not a functional gap.

## Go / No-Go
**GO.** Every `ACCEPTANCE_TESTS.md` item passes (see `ACCEPTANCE_REPORT.md`); the full `DEMO_SCRIPT.md` sequence has been run end-to-end on real hardware (see `INTEGRATION_REPORT.md`); the automated regression suite (37 tests) passes. The one disclosed content gap (Amharic/Arabic dialogs) does not block an English-language demonstration and does not indicate broken code — wake word detection, language selection, and fallback responses all work correctly in Amharic and Arabic already.
