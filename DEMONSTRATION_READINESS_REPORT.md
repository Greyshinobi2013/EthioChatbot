# Demonstration Readiness Report (Final Audit)

This supersedes the Milestone 8 version. It is an independent, skeptical re-audit of the entire implementation against `README.md`, `ARCHITECTURE.md`, `STATE_MACHINE.md`, `EVENTS.md`, `SCENARIOS.md`, `DEMO_SCRIPT.md`, and `ACCEPTANCE_TESTS.md` — re-reading the actual current code rather than relying on prior milestone self-reports. **No code was changed to produce this report**; findings are identified and prioritized only, per this task's scope.

**Verdict: GO, with three findings worth fixing before a high-stakes demo** (flagged 🔴 below). Everything else is disclosed risk with a working mitigation, or a low-probability edge case.

---

## 1. Demo-breaking risks

### 🔴 No retry after a service fails to acquire its device — permanent, silent death for the rest of the session
`camera_service.run_camera_service()`, `audio_service.run_audio_service()` (Whisper load failure specifically), and `vad_handler`'s open-mic path all follow the same pattern: if the resource fails to acquire **once**, the thread sets an `ERROR` status and returns for good. There is no reconnect/retry loop anywhere. Concretely:
- If the webcam is briefly busy at the exact moment `app.py` bootstraps (another process holds it, a USB re-enumeration hiccup), face recognition is dead for the entire session — the only fix is a full app restart.
- If `whisper.load_model()` fails for **any** reason at startup — most realistically, no internet on first run before the model is cached, or a flaky connection mid-download — `audio_service`'s thread returns immediately at that point and **never reaches its main loop at all**. Wake-word detection and question-answering are both silently dead, with only a log line (`microphone_status: ERROR` on the Dashboard) as any indication.

This is the single highest-impact risk in the project: a transient, one-time failure at the exact moment of startup permanently disables a whole subsystem with no visible, in-context recovery path.
**Mitigation available today**: run the app once before the demo so Whisper's model is already cached (see pre-demo checklist below) — this removes the most likely trigger. The underlying lack of retry logic is still a legitimate hardening item.

### 🔴 A failed or missing response plays nothing — no fallback-of-fallback sound
`conversation_manager.play_response()` catches playback failures and logs them, but the *observable result* is silence: no error tone, no "something went wrong" cue, nothing on the physical robot. From an audience's perspective, a corrupted upload, a missing file, or any playback exception is indistinguishable from the robot simply ignoring the question. This applies to the greeting, the matched response, and — worst case — the fallback (`unknown_question.wav`) itself: if the fallback audio for the active language is ever missing, the "no match" path also produces silence instead of a fallback-of-fallback.
**Mitigation available today**: the pre-demo checklist below confirms all 15 audio assets exist for all 3 languages (currently true). The gap is that nothing detects this *at runtime* if it changes.

### 🔴 `config/settings.json` currently deviates from the spec's default
Checked directly: `whisper_model` is currently `"base"`, not the `"medium"` README.md mandates as the default. This is not a code bug — it's live configuration drift (someone used the Settings page, or a prior test run's revert didn't take before a later change). Practically, **`base` is faster and more demo-reliable than `medium`** on CPU-only hardware (measured: ~2s vs ~24s per 3-second chunk), so this particular drift *helps* rather than hurts a live demo. Flagging it because it's a silent divergence from the documented spec default that a strict grading pass against README.md would catch, and because config drift in general (see the shutdown-mechanism finding below for *why* it can only be fixed by manual file edit or restart) is worth being aware of before a demo.

### Non-blocking: Whisper `medium` latency (previously disclosed, unchanged)
~24s to transcribe a 3-second clip with no GPU. Correctness is unaffected, only responsiveness. Already mitigated by the current `base` setting above, or the Settings page if `medium` is restored.

---

## 2. Missing acceptance criteria

- **"Multiple users supported"**: proven at the algorithm level (a synthetic 3-user disambiguation test picks the correct nearest match and correctly rejects a non-match), and the `load_faces()`/`match_face()` design is inherently multi-user (a plain loop over all enrolled users). **Never demonstrated live with two different real enrolled people** — only one human tester was available through the entire build. Low risk (the code path doesn't distinguish "1 user" from "N users" structurally) but genuinely untested end-to-end with real biometric data from two people.
- **Amharic / Arabic dialog content**: wake-word detection, language selection, and fallback response all work correctly and are tested in both languages. **No actual dialog content exists** (`dialog_config.json`'s `amharic`/`arabic` arrays are empty) because the spoken content of the pre-recorded Amharic/Arabic clips was never verified by listening, and fabricating `user_text` mappings for unheard audio risked shipping wrong data. A demo in these languages would reach `CONVERSATION_ACTIVE` correctly but every question would hit the fallback response. This was disclosed as early as Milestone 4 and hasn't changed.
- **ARCHITECTURE.md's "Shutdown Sequence"** (Stop Service Threads → Stop Playback → Release Webcam → Release Microphone → Persist State → Shutdown Logging → Exit) is **entirely unimplemented**. `AppState.stop_event` exists and every service thread correctly responds to it (proven by the automated test suite and by test scripts throughout development) — but nothing in the shipped `app.py` or any page ever calls `.set()` on it. The only way to stop the app is to kill the `streamlit run` process directly; there is no in-app graceful shutdown, and no explicit resource release beyond what the OS reclaims automatically on process exit. Not covered by `ACCEPTANCE_TESTS.md` (which has no shutdown tests), but it is a documented architecture requirement that doesn't exist in the implementation.

---

## 3. Stability issues

- **No protection against a second concurrent bootstrap.** `get_app_state()` relies entirely on `st.cache_resource` never being invalidated while services are running. If a user clicks Streamlit's own "Clear cache" (available by default in its hamburger menu) while the app is live, the next rerun calls `bootstrap_app()` again — a second camera thread, second mic thread, and a second full set of event-bus subscribers, all racing the first set over the same hardware and double-handling every event (e.g., the greeting would play twice, from two different state objects). Low probability during a controlled demo, but a single accidental click away.
- **`utils/conversation_manager.monitor_timeout()` has no top-level exception guard**, unlike the other three service threads (camera/audio/VAD all wrap their main loop in `except Exception: logger.exception(...)`). Nothing in the current code path is known to raise there, but if it ever does, the timeout/return-to-idle mechanism would die silently and *not even go through the app's own logger* (an uncaught exception in a thread target just prints to stderr by default) — the one service whose failure mode is actually worse than the others'.
- **VAD's mic-open retry has no cooldown.** If the device stays busy for an extended period (not just the brief expected handoff window), `monitor_interruptions` retries in a tight loop for the entire duration of that `PLAYING_AUDIO` episode — no crash, but unnecessary CPU churn and log spam instead of backing off.
- **`playback.py`'s module-level state** (`_state`, `_segment_started_at`, `_elapsed_before_segment`) is read/written from multiple threads (the conversation thread via `play_audio`, the VAD thread via `pause_audio`/`resume_audio`) without a lock — only mixer *initialization* is lock-protected. The realistic failure mode is a stale position read or a no-op pause/resume in an extremely narrow race window (a track finishing naturally at the exact instant a VAD interruption fires), not a crash.
- **Log file and stray `__pycache__` are committed to git** (`logs/app.log`, 12 `.pyc` files). Not a runtime risk, but a rough edge that can cause confusing diffs or a misleading "already ran" log on a fresh clone.

---

## 4. Error-handling weaknesses

- **Enrollment page only catches `FaceEnrollmentError`.** `enroll_face()` can also raise from `cv2`/`dlib` internals (a malformed image) or plain `OSError` (unwritable `faces/` directory) — none of those are caught by `pages/2_Enroll_Face.py`'s `except FaceEnrollmentError`, so they'd surface as a raw Streamlit traceback in front of an audience instead of a clean error message.
- **No `user_id` sanitization before it becomes a directory name** (`faces/<user_id>/`). A user ID containing `/` or `..` would be interpreted as path segments by `pathlib`. Low risk for a single-operator local tool, but unvalidated input becoming a filesystem path is worth closing.
- **`save_configuration()`/`save_scenarios()` don't handle write failures.** If `config/settings.json` or `dialog_config.json` becomes unwritable (permissions, full disk) mid-demo, the Settings/Scenario Management pages would show a raw traceback rather than a friendly error, since none of the three admin pages wrap these calls in `try/except`.
- **`handle_transcription_ready()` doesn't guard `load_scenarios()`.** If `dialog_config.json` is malformed at the exact moment a question is asked (e.g., a save from the Manage Scenarios page is interrupted, or someone hand-edits the file mid-demo), `load_scenarios()` raises `ScenarioError` uncaught inside the handler. The event bus's dispatch wrapper catches it one level up (so the *app* doesn't crash), but the practical effect is that **that specific question gets silently dropped — no response, not even the fallback** — which is a worse audience-facing outcome than the exception itself.
- **No delete confirmation** on the Manage Scenarios page (wake words and dialogs both delete immediately on click, no "are you sure?"). An accidental double-click during a live edit has no undo.

---

## 5. Missing asset references

**None currently missing** — verified directly, not assumed:
- Both dlib model files (`models/shape_predictor_68_face_landmarks.dat`, `models/dlib_face_recognition_resnet_model_v1.dat`) are present and git-tracked.
- All 15 audio assets (5 clips × 3 languages) exist on disk.
- Every `response_audio` path currently in `dialog_config.json` resolves to a real file.

**The code-level gap that matters even though nothing is missing today**: `utils/face_recognition.py` loads both dlib model files at **module import time**, completely unguarded:
```python
_shape_predictor = dlib.shape_predictor(str(SHAPE_PREDICTOR_PATH))
_face_rec_model = dlib.face_recognition_model_v1(str(FACE_RECOGNITION_MODEL_PATH))
```
If these files are ever absent (a shallow/partial clone, a `.gitignore` added carelessly in the future, manual deletion to save disk space), **the entire application fails to import and start** — not a graceful degraded mode, a hard crash on `streamlit run app.py` before anything renders. Because they're currently committed directly in git (not LFS, ~120MB combined), a normal `git clone` carries them along, which is why this hasn't manifested — but the code has zero defense if that ever changes.

`requirements.txt` also has no CPU-only pin for `torch`. A plain `pip install -r requirements.txt` on a fresh machine can resolve a GPU/CUDA build that pulls 5GB+ of unneeded packages — this is not hypothetical, it's exactly what happened during this project's own development (documented in the Milestone 3 report) and was worked around manually (installing from PyTorch's CPU wheel index) rather than fixed in `requirements.txt` itself. A demo machine with a constrained disk could hit the same failure during setup.

---

## Pre-demo checklist (unchanged, still correct)
1. `pip install -r requirements.txt`. If disk space is limited, install CPU-only `torch` first via `--index-url https://download.pytorch.org/whl/cpu` before running this, per the finding above.
2. Confirm both `models/*.dat` files are present (they are, and are git-tracked — just don't `git clean`/shallow-clone in a way that could drop them).
3. **Run the app once before the demo**, fully through to a recognized face, so Whisper's model is cached and the highest-severity risk in this report (silent audio-service death on first-run download failure) is neutralized.
4. Enroll the presenter's face ahead of time.
5. `python -m unittest discover tests` → should show `OK` (37 tests).
6. Decide `medium` vs `base` for `whisper_model` deliberately (currently `base`) rather than leaving it to whatever it happens to be set to.

## Go / No-Go
**GO for a standard, attended demonstration** — the operator (someone who ran the pre-demo checklist and can restart the process if needed) is an implicit safety net for every 🔴 finding above. **Not yet hardened for an unattended kiosk or a demo run by someone unfamiliar with the codebase**, where a single first-run network hiccup or an accidental cache-clear click has no in-app recovery path. The three 🔴 items are the ones worth fixing first if this moves beyond a supervised demo.
