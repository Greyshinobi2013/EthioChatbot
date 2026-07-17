# EthioChatbot V2 — Release Candidate Report

**Date:** 2026-07-17
**Scope:** Milestones 1–13 (Foundation through End-to-End Integration)
**Status:** Release Candidate — see Final Verdict (Section 10)

This report summarizes the as-built state of EthioChatbot V2 following full-system integration testing. It is a synthesis of implementation and verification work across all 13 milestones; it does not itself change any code.

---

## 1. Final Architecture Summary

EthioChatbot V2 is a fully offline, event-driven, finite-state-machine-controlled conversational robot. It is deterministic by design: no LLM, embedding search, or generative model is used anywhere in the conversation path — every spoken response is a prerecorded audio file selected by exact/keyword text matching.

**Four-layer architecture**, as specified in ARCHITECTURE.md:

```
Presentation Layer   → Streamlit pages (pages/*.py): monitoring & administration only
Service Layer        → 8 independent services, communicating exclusively via events
Core Layer            → EventBus + FiniteStateMachine + StateManager (single source of truth)
Persistence Layer     → JSON (users, scenarios, settings) + WAV/MP3 files; no database server
```

**Two distinct runtime entry points**, both served by the same `app.py`:

- **CLI path** (`python app.py` → `Application.startup()` → `main()`): foundation-only — config, logging, event bus, state, FSM, empty service registry. No hardware touched. Fast (~3s), used for lightweight regression checks throughout development.
- **Full-system path** (`Application.start_full_system()`, exposed to Streamlit via `get_running_application()`): builds and starts all 8 services, wired to real camera/microphone hardware. Cached as a process-wide singleton via `st.cache_resource` so it survives Streamlit's per-interaction reruns — the architectural decision made at project inception to reconcile Streamlit's execution model with an always-on robot engine.

The Event Bus is the sole communication mechanism between services (no direct service-to-service calls); the FSM is the sole authority for state transitions, validated against a fixed transition graph; the StateManager is the single shared, thread-safe source of truth for runtime state that both the FSM and every service read and write.

---

## 2. Implemented Modules

| Module | Milestone | Purpose |
|---|---|---|
| `app.py` | 1, 11, 13 | Entry point: config load/save, logging, service registry, CLI lifecycle, and the `start_full_system()`/`get_running_application()` singleton for Streamlit |
| `utils/logger.py` | 1 | Centralized logging: console + size-bounded rotating file handler |
| `utils/state_manager.py` | 1 | Thread-safe shared state: `current_state`, `current_language`, `active_users`, `camera_status`, `playback_status`, `wake_word_status` |
| `utils/event_bus.py` | 2 | Thread-safe, synchronous, in-process publish/subscribe bus |
| `utils/fsm.py` | 2 | 12-state finite state machine; validated transition graph; rejects and logs invalid transitions |
| `utils/face_enrollment.py` | 3, 13 | Face detection/embedding for still-image enrollment; owns the shared dlib model singleton and the thread-safety lock protecting it |
| `utils/face_recognition.py` | 4, 12, 13 | Pure recognition engine: embedding comparison, confidence scoring, identity matching against enrolled users |
| `utils/camera_service.py` | 4, 13 | Camera capture thread: detect every frame, recognize every 10th frame, `last_seen`/`FACE_LOST` tracking, resolves `FACE_LOST_CHECK` for every entry path |
| `utils/greeting_service.py` | 5 | Priority-sorted sequential greeting playback (English-only, non-interruptible) |
| `utils/whisper_utils.py` | 6, 13 | Whisper `base` model (loaded once); wake-word detection; forced-language transcription during conversation |
| `utils/scenario_engine.py` | 7, 11 | Deterministic scenario loading, per-language lookup caches, exact/keyword matching, fallback resolution, and CRUD for the Manage Scenarios page |
| `utils/playback.py` | 8 | WAV/MP3 playback engine with sample-accurate pause/resume/restart and position tracking |
| `utils/vad_handler.py` | 9 | WebRTC VAD speech/silence detection driving the full interruption workflow |
| `utils/audio_service.py` | 13 | Continuous microphone capture, hardware-rate resampling, per-utterance capture bounded by a hard cap, routes audio to VAD/Whisper by FSM state |
| `utils/conversation_manager.py` | 10, 13 | Language context lifecycle, scenario→playback bridging, 30s conversation timeout, `RETURN_TO_IDLE` cleanup |
| `pages/1_Dashboard.py` | 11 | Live monitoring: state, language, camera feed, active users, logs |
| `pages/2_Enroll_Face.py` | 3 | Face enrollment UI (webcam or upload) |
| `pages/3_Manage_Scenarios.py` | 11 | Scenario add/edit/delete UI |
| `pages/4_Settings.py` | 11 | Camera/Whisper/VAD/timeout settings UI |

All Streamlit pages are business-logic-free per ARCHITECTURE.md's restriction; all validation and persistence lives in the `utils/` modules above.

---

## 3. Implemented Services

Eight services implement the `Service` protocol (`name`, `start()`, `stop()`) and are registered with `ServiceRegistry` in `Application.start_full_system()`, started in dependency order and stopped in reverse:

| # | Service (`.name`) | Owns | Key responsibility |
|---|---|---|---|
| 1 | `camera_service` | Camera thread | Face detection/recognition cadence, persistence tracking, `FACE_LOST_CHECK` resolution |
| 2 | `greeting_service` | Greeting thread | Priority-sorted sequential greeting playback |
| 3 | `whisper_service` | Whisper model (no thread) | Wake-word detection, forced-language transcription |
| 4 | `scenario_engine` | Scenario cache (no thread) | Deterministic question→audio matching |
| 5 | `playback_service` | Playback watcher thread | Interruptible response playback |
| 6 | `vad_handler` | (no thread; frame-driven) | Interruption workflow orchestration |
| 7 | `audio_service` | Microphone thread | Continuous capture, utterance segmentation, routing |
| 8 | `conversation_manager` | Timeout watcher thread | Language context, timeout, `RETURN_TO_IDLE` cleanup |

**Architectural note:** face recognition itself (`face_recognition.py`) is not independently registered — it is a stateless engine owned and called by `camera_service`, matching ARCHITECTURE.md's description of the Face Recognition Service as embedded in the camera pipeline rather than a separately threaded process. This is a deliberate M4 design decision, not a gap.

All 8 services were verified starting and stopping cleanly together against real camera and microphone hardware (Milestone 13).

---

## 4. Event Bus Summary

Thread-safe, synchronous, in-process publish/subscribe (`utils/event_bus.py`). A publishing thread's `publish()` call dispatches to every subscriber before returning; one subscriber's exception is isolated and does not block others.

**Event catalog, as actually implemented** (grouped by category; matches EVENTS.md except where noted):

- **System:** `SYSTEM_STARTUP`, `SYSTEM_SHUTDOWN`
- **Face:** `FACE_DETECTED`, `FACE_RECOGNIZED`, `MULTIPLE_USERS_RECOGNIZED`, `FACE_UNKNOWN`, `FACE_LOST`, `ALL_USERS_LOST`
- **Greeting:** `GREETING_STARTED`, `USER_GREETING_STARTED`, `USER_GREETING_FINISHED`, `GREETING_FINISHED`, `PRIORITY_LIST_READY`
- **Wake word / language:** `WAKE_WORD_DETECTED`, `WAKE_WORD_REJECTED`, `LANGUAGE_CONTEXT_SET`, `LANGUAGE_CONTEXT_CLEARED`
- **Conversation:** `CONVERSATION_STARTED`, `CONVERSATION_ENDED`, `TRANSCRIPTION_STARTED`, `TRANSCRIPTION_READY`
- **Scenario:** `SCENARIO_MATCHED`, `SCENARIO_NOT_FOUND`, `FALLBACK_SCENARIO_SELECTED`
- **Playback:** `PLAYBACK_STARTED`, `PLAYBACK_PAUSED`, `PLAYBACK_RESUMED`, `PLAYBACK_STOPPED`, `PLAYBACK_FINISHED`
- **Interruption:** `INTERRUPTION_DETECTED`, `INTERRUPTION_AUDIO_STARTED`, `INTERRUPTION_AUDIO_FINISHED`, `INTERRUPTION_CLEARED`
- **Timeout:** `TIMEOUT_OCCURRED`
- **State:** `STATE_CHANGED`, `IDLE_ENTERED`
- **Gap-fill (documented deviation from EVENTS.md):** `FACE_LOST_CHECK_PASSED` — introduced in Milestone 2's design as the missing resolution event for `FACE_LOST_CHECK`'s "users remain" outcome (EVENTS.md only names `ALL_USERS_LOST` for the "no users remain" outcome), and actually implemented by `camera_service.py` in Milestone 13.

`ALL_USERS_LOST` and `IDLE_ENTERED` are used as the authoritative event names throughout (per the explicit Milestone 2 correction), replacing STATE_MACHINE.md's inconsistent `NO_ACTIVE_USERS`/`RETURN_TO_IDLE_COMPLETE`.

---

## 5. FSM Summary

12 states (`utils/fsm.py`), matching STATE_MACHINE.md exactly: `IDLE`, `FACE_DETECTED`, `FACE_RECOGNIZED`, `PRIORITY_SORTING`, `GREETING`, `WAITING_FOR_WAKE_WORD`, `CONVERSATION_ACTIVE`, `PLAYING_AUDIO`, `INTERRUPTED`, `TIMEOUT`, `FACE_LOST_CHECK`, `RETURN_TO_IDLE`.

**Transition table** (17 entries; `(state, event) → next_state`):

```
IDLE                  --FACE_DETECTED-->            FACE_DETECTED
FACE_DETECTED         --FACE_RECOGNIZED-->           FACE_RECOGNIZED
FACE_RECOGNIZED       --MULTIPLE_USERS_RECOGNIZED--> PRIORITY_SORTING
PRIORITY_SORTING      --PRIORITY_LIST_READY-->       GREETING
GREETING              --GREETING_FINISHED-->         WAITING_FOR_WAKE_WORD
WAITING_FOR_WAKE_WORD --WAKE_WORD_DETECTED-->         CONVERSATION_ACTIVE
WAITING_FOR_WAKE_WORD --FACE_LOST-->                  FACE_LOST_CHECK
WAITING_FOR_WAKE_WORD --ALL_USERS_LOST-->             FACE_LOST_CHECK
CONVERSATION_ACTIVE   --SCENARIO_MATCHED-->           PLAYING_AUDIO
CONVERSATION_ACTIVE   --TIMEOUT_OCCURRED-->           TIMEOUT
PLAYING_AUDIO         --PLAYBACK_FINISHED-->          CONVERSATION_ACTIVE
PLAYING_AUDIO         --INTERRUPTION_DETECTED-->      INTERRUPTED
INTERRUPTED           --INTERRUPTION_CLEARED-->       PLAYING_AUDIO
TIMEOUT               --LANGUAGE_CONTEXT_CLEARED-->   FACE_LOST_CHECK
FACE_LOST_CHECK       --ALL_USERS_LOST-->             RETURN_TO_IDLE
FACE_LOST_CHECK       --FACE_LOST_CHECK_PASSED-->     WAITING_FOR_WAKE_WORD
RETURN_TO_IDLE        --IDLE_ENTERED-->               IDLE
```

Validation is (from_state → to_state) based, derived automatically from this table — any pair not listed is rejected and logged (`STATE_TRANSITION_REJECTED`), confirmed against all three of STATE_MACHINE.md's documented invalid-transition examples (`IDLE→PLAYING_AUDIO`, `GREETING→INTERRUPTED`, `PLAYING_AUDIO→IDLE`).

**Milestone 13 finding:** two edges in this table — `RETURN_TO_IDLE→IDLE` and `FACE_LOST_CHECK→WAITING_FOR_WAKE_WORD` (via the timeout-driven path) — were structurally present since Milestone 2 but **unreachable in practice** until Milestone 13, because nothing published the events that trigger them. Both are now fixed and verified (Section 7 has details).

---

## 6. Raspberry Pi Deployment Checklist

| Item | Status |
|---|---|
| Camera resolution 640×480 | ✅ Configured and verified (`config/settings.json`, module defaults) |
| Recognition every 10th frame, detection every frame | ✅ Configured and verified; redundant double-detection bug found and fixed (Milestone 12, ~25% CPU reduction on recognition frames) |
| Whisper `base` model | ✅ Configured; loads once, cached, reused (verified: exactly 1 `load_model` call across multiple service instances) |
| Face embedding / scenario dictionary / language-context caching | ✅ All verified to incur zero redundant disk reads or recomputation regardless of call volume |
| Memory policy (`latest_frame`, `latest_audio_chunk` only) | ✅ Verified directly; sustained real capture (camera + microphone) shows flat memory; growth under heavy repeated-cycle load proven bounded and OS-reclaimable (`malloc_trim` test), not a leak |
| `requirements.txt` present and pinned | ✅ Present; **caveat:** pinned versions were verified in this dev environment only — `dlib`/`opencv-python` wheel availability and build time on Raspberry Pi OS (ARM) should be confirmed before deployment, as these can be slow to compile from source on Pi-class hardware |
| dlib model files (`shape_predictor_68_face_landmarks.dat`, `dlib_face_recognition_resnet_model_v1.dat`, ~120MB) | ⚠️ Not committed to git (by design, to keep repo size reasonable) — must be fetched from dlib.net (one-time internet access) or copied onto the Pi before first run |
| Whisper `base` model weights (~150MB) | ⚠️ Must be downloaded once (via `whisper.load_model("base")`'s automatic fetch) or pre-seeded into the Pi's `~/.cache/whisper/` before offline operation |
| Microphone sample-rate compatibility | ✅ Handled generically — `audio_service.py` probes the device's supported rate and resamples to 16kHz; this dev environment's hardware only supported 48kHz capture, confirming the resampling path is exercised in practice, not just theoretical |
| Runtime network calls | ✅ Confirmed zero — grepped `utils/` and `app.py` for any HTTP/socket usage; none found. Fully offline once the two one-time asset downloads above are complete |
| Real Raspberry Pi 4 hardware validation | ❌ **Not performed.** All testing in this project ran on a similarly-scoped but more powerful sandboxed x86 environment. Absolute timing (Whisper inference latency, recognition throughput) will differ on real Pi 4 silicon and has not been measured there |

---

## 7. Known Limitations

1. **Amharic/Arabic wake-word and speech-recognition accuracy is not verified with real native speech.** This environment has no human speaker and no microphone input source other than ambient noise; synthetic `espeak-ng` voices for these two languages are low enough quality that Whisper's `base` model frequently mis-transcribes them (confirmed with both `base` and `medium` models). The matching *logic* downstream of transcription (normalization, exact/keyword matching, event wiring) is fully verified directly; only the audio-to-text step for these two languages lacks real-speech confidence. **English is fully verified with real audio throughout.**
2. **Not validated on actual Raspberry Pi 4 hardware.** See Section 6.
3. **Personalized greeting audio files are placeholders.** `audio/{english,amharic,arabic}/greetings/{manager,natnael,visitor}.wav` are still 0 bytes; the system correctly and automatically falls back to `greeting.wav`, but real personalized recordings would improve the demo.
4. **`dialog_config.json` is seeded with only two scenarios per language** (name, goodbye), matching DEMO_SCRIPT.md's examples. A real deployment should populate a fuller scenario set via the Manage Scenarios page before a live demonstration with unscripted questions.
5. **Repeated IDLE re-entry cycles were verified once, not exhaustively.** Milestone 13's full-system test exercises exactly one full `IDLE → ... → IDLE → re-entry` cycle; nothing in the code suggests state would degrade across many repeated cycles (all relevant state is explicitly reset on `RETURN_TO_IDLE`), but this was not stress-tested across dozens of cycles.
6. **Memory allocator fragmentation under sustained heavy use.** Repeated Whisper/dlib inference cycles show RSS growth that plateaus at a bounded ceiling (verified: not unbounded) and is fully reclaimable via `malloc_trim()` (verified: 163MB reclaimed in one test). No automatic periodic-trim mitigation is implemented, since it wasn't demonstrated to be operationally necessary within this environment's testing — worth monitoring on real Pi hardware over long demo sessions.
7. **No concurrent-multi-speaker handling in conversation audio capture.** `audio_service.py` captures one utterance at a time via VAD speech/silence boundaries; simultaneous overlapping speech from multiple people during a live conversation isn't specifically disambiguated (enrollment's "largest face" tie-break is unrelated to this — it applies to face images, not simultaneous audio).
8. **No screenshots or human visual inspection of the live camera feed / Dashboard UI.** All UI verification used Streamlit's headless `AppTest` harness plus programmatic checks (frame shape, widget state, real file writes) rather than a human looking at rendered pixels.

---

## 8. Demonstration Readiness Assessment

**All 20 steps of DEMO_SCRIPT.md pass against the real, fully-integrated system** (`app.start_full_system()`), using real dlib face recognition on real photos, real Whisper transcription of real synthesized speech, real pygame audio playback, and real interruption/resume timing — not mocks, and not isolated per-module tests.

**Three integration bugs were found and fixed** during this full-system validation, each of which would have been demonstration-blocking if left undiscovered:

1. **Segfault under concurrent dlib access** — a live camera recognition thread running concurrently with face enrollment reliably crashed the process. Fixed with a shared inference lock; reproduced the original crash scenario post-fix with zero errors.
2. **`RETURN_TO_IDLE` could never complete** — the robot would get permanently stuck after all users left, never actually reaching `IDLE`. Fixed by having `conversation_manager.py` perform the documented cleanup and publish the missing `IDLE_ENTERED` event.
3. **`FACE_LOST_CHECK` could never resolve when reached via a conversation timeout** (as opposed to a direct face-loss detection) — the robot would get stuck instead of returning to `WAITING_FOR_WAKE_WORD`. Fixed by having `camera_service.py` resolve this state for every entry path, not just its own.

**Readiness by conversation language:**

| Language | Wake word | Conversation | Confidence |
|---|---|---|---|
| English | ✅ Real audio verified | ✅ Real audio verified, including interruption/resume | **Demo-ready** |
| Amharic | Structurally verified (logic + events); real speech untested | Same | **Ready pending a real-speaker test pass** |
| Arabic | Structurally verified (logic + events); real speech untested | Same | **Ready pending a real-speaker test pass** |

**Recommended pre-demonstration checklist:**
- [ ] Run the wake-word and question flow with real Amharic and Arabic speakers
- [ ] Run the full 20-step demo on actual Raspberry Pi 4 hardware and confirm acceptable latency
- [ ] Record real personalized greetings for enrolled demo participants (optional — fallback already works correctly)
- [ ] Populate `dialog_config.json` with the actual questions planned for the live demonstration
- [ ] Do one visual/manual pass of the Streamlit dashboard and camera feed on real hardware

---

## 9. Acceptance Coverage Summary

Against ACCEPTANCE_TESTS.md's 17 sections: **13 fully verified, 4 verified with disclosed caveats.** All four caveated sections (7: Wake Word Detection, 9: Whisper Tests, 15: Return To Idle & Re-Entry, 16: Raspberry Pi Performance) trace back to the same two environmental limitations — no real Amharic/Arabic speech input available, and no physical Raspberry Pi 4 to test on — not to unresolved functional defects. Every acceptance item that *could* be exercised in this environment was exercised with real components (real hardware where available, real models, real audio), not mocks.

The hardest integration surfaces — pause/resume during interruption, timeout-driven context clearing, partial/complete face loss, and re-entry after returning to idle — all have direct, end-to-end evidence, including the three bugs in Section 8 that only full-system testing could have surfaced.

---

## 10. Final Verdict

**All 13 milestones are complete.** Every explicit completion criterion in IMPLEMENTATION_PLAN.md has been met, and the system has been validated end-to-end against real hardware and real models within the limits of this development environment.

**Verdict: Conditional Release Candidate — GO for demonstration, pending the pre-demonstration checklist in Section 8.**

This is not an unconditional sign-off: two categories of validation remain genuinely untested rather than merely unlikely to matter — real Amharic/Arabic speech recognition, and behavior on actual Raspberry Pi 4 hardware. Both are bounded, well-understood gaps with a clear closing action, not open design questions. Everything within reach of this environment — the full event-driven pipeline, the finite state machine (including the three integration bugs this milestone's testing specifically exists to catch), multilingual scenario matching, interruptible playback, and the complete 20-step demonstration script — is verified working end-to-end with real components.
