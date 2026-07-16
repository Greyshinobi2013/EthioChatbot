# Integration Report

## Architecture as built

```
app.py (bootstrap only)
  ├── loads config/settings.json, initializes logging, shared AppState
  ├── registers 4 background service threads:
  │     camera_service    -- opens webcam once, continuous detect+recognize
  │     audio_service      -- opens mic per WAITING_FOR_WAKE_WORD/CONVERSATION_ACTIVE session
  │     vad_handler         -- opens mic per PLAYING_AUDIO/INTERRUPTED session
  │     timeout_monitor     -- polls CONVERSATION_ACTIVE duration
  └── all inter-service communication goes through utils/event_bus.py
        (no service calls another service directly)

pages/*.py (Streamlit UI, no business logic)
  └── import get_app_state from app.py (st.cache_resource singleton,
      shared across all pages in the real running server process)
```

Services never call each other directly; they publish/subscribe through `utils/event_bus.py`, and `utils/conversation_manager.py` is the only module that reacts to events and drives `utils/state_manager.py`'s validated FSM. This was verified structurally (code review) and behaviorally (every milestone's live tests + the Milestone 8 full run all show the event-only communication path in the logs).

## Full workflow trace (Milestone 8 live run, real hardware)

```
Face Enrollment  → enroll_face() via live webcam capture, real file written
Face Recognition → FACE_DETECTED, FACE_RECOGNIZED (confidence=0.77, live)
Greeting         → GREETING_STARTED, real audio played, GREETING_FINISHED
Wake Word        → WAKE_WORD_DETECTED (english, "hello robot")
Language Sel.    → LANGUAGE_SELECTED, current_language=english
Conversation Act.→ CONVERSATION_ACTIVE reached
Whisper          → TRANSCRIPTION_STARTED, TRANSCRIPTION_READY
Scenario Match   → SCENARIO_MATCHED ("what is your name" -> name.wav)
Audio Playback   → PLAYBACK_STARTED, real audio played, PLAYBACK_FINISHED
                    (second turn: SCENARIO_NOT_FOUND -> fallback audio, also verified)
Timeout          → TIMEOUT_OCCURRED after configured inactivity window
Return To Idle   → RETURN_TO_IDLE, state=IDLE, recognized_user/current_language cleared
```

Camera, audio, VAD, and timeout threads all shut down cleanly on `stop_event` at the end (confirmed via `thread.join()`, none left alive).

Some steps in this particular run used the project's established, transparently-disclosed fallback: where a step needs precisely-timed live human speech (a specific wake phrase, a specific question, speaking exactly during a playback window) that cannot be scripted, the real event was published directly through the real event bus instead of waiting indefinitely for it to happen on cue. This exercises the identical code path camera_service/audio_service/vad_handler use in production — only the *trigger* is manual, not the handling. Organic (fully hands-off) success for face recognition, wake-word-adjacent speech pickup, and interruption has each been independently demonstrated live in earlier milestones (M2 face recognition, M6 ambient speech pickup, M5 and M6 organic interruption) and is not re-litigated here.

## Bugs found and fixed (consolidated across the whole project)

| # | Milestone | Bug | Fix |
|---|---|---|---|
| 1 | 2 | `app.py` ran `main()` on plain `import`, so a test importing it re-triggered a full bootstrap and tried to reopen the camera | Guarded with `if __name__ == "__main__"` |
| 2 | 2 | `enroll_face()` validated the in-memory frame but not the JPEG actually written to disk; a marginal detection could pass pre-save and fail post-save | Re-validate the saved file immediately; delete and raise if it fails |
| 3 | 3 | Microphone `InputStream` hardcoded to 16kHz; this device's native rate is 48kHz, so it failed to open at all | Query native rate at runtime, resample to 16kHz with NumPy interpolation |
| 4 | 3 | `handle_face_recognized` had no state guard, so camera flicker replayed the entire greeting on a loop | Only proceed when `current_state == FACE_DETECTED` |
| 5 | 5 | `pygame.mixer.music` (single stream) can't pause a response and play an interruption notice independently | Rebuilt on `pygame.mixer.Channel` with separate response/notification channels |
| 6 | 5 | Position tracking froze at the last pause point after a track finished naturally instead of reflecting full duration | Fold the final segment's elapsed time in before clearing the timer |
| 7 | 6 | `audio_service` held the microphone open for its whole thread lifetime; `vad_handler` needs the same device during playback and this hardware doesn't support two simultaneous opens | Session-scoped mic opening in `audio_service`, closed outside its listening states |
| 8 | 6 | Even session-scoped, a blocking 3-second read could hold the mic while `vad_handler` needed it | Read in 0.3s sub-chunks so state changes are noticed within ~40ms |
| 9 | 6 | `pkg_resources` (used by `webrtcvad`) was removed by very new `setuptools` | Pinned `setuptools<81` in `requirements.txt` |
| 10 | 8 (this milestone) | Test-script timing bug: an 8s test-only `conversation_timeout` raced a 20s "wait for organic event" window, causing the conversation to time out and reset before a fallback injection landed — the FSM correctly rejected the late, stale-state event | Recalibrated test windows so injected fallbacks always land comfortably before any timeout risk. **Not a product bug**: the FSM's rejection of a stale-context event was exactly correct behavior. |

Ten issues found and fixed across the full build, all confirmed resolved by rerunning the relevant test after each fix — none were left as known-but-unfixed defects.

## Known limitations (disclosed, not defects)
- **Amharic/Arabic dialog content**: infrastructure (wake words, language selection, fallback) works; no scenario dialogs authored since the spoken content of the pre-recorded clips wasn't verified by listening. Populating this is a content task for whoever can confirm the clips' actual content, via the Manage Scenarios page.
- **`medium` Whisper model is slow on this CPU** (~24s per 3s audio chunk, no GPU). Disclosed in M3; mitigated by the Settings page's model picker. Demo default stays `medium` per README's spec regardless.
- **Settings do not hot-reload**: every service reads `config` once at its own thread startup; a settings change requires an app restart to take effect. Disclosed on the Settings page itself.
- **`st.camera_input()` deliberately not used** on the Enrollment page — this webcam doesn't support two simultaneous consumers, so enrollment reuses `camera_service`'s already-open feed instead.

## Test suite added this milestone
`tests/` (previously empty): `test_text_normalization.py` (8 tests), `test_scenario_matching.py` (16 tests), `test_state_machine.py` (12 tests), `test_integration_e2e.py` (1 full-workflow test, real event bus/FSM/scenario engine/playback, no hardware dependency). **37/37 pass.** Run with `python -m unittest discover tests`.
