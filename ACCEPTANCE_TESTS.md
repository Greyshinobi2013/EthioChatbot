# ACCEPTANCE TESTS

## Purpose

These acceptance tests determine whether the project is complete.

A feature is considered complete only if its acceptance criteria pass.

---

# Startup Tests

[ ] Application starts successfully

[ ] Settings load successfully

[ ] Logging initializes successfully

[ ] Webcam initializes successfully

[ ] Microphone initializes successfully

[ ] Event Bus initializes successfully

[ ] State Machine initializes successfully

[ ] Application enters IDLE state

---

# Face Enrollment Tests

[ ] Webcam capture works

[ ] Image upload works

[ ] Face saved successfully

[ ] User appears in enrollment list

---

# Face Recognition Tests

[ ] Faces load successfully

[ ] Face detection works

[ ] Face recognition works

[ ] Multiple users supported

[ ] Confidence score returned

---

# Greeting Tests

[ ] Greeting triggers automatically

[ ] Greeting audio plays

[ ] FSM transitions correctly

---

# Wake Word Tests

[ ] Wake word detection works

[ ] Invalid wake words rejected

[ ] Wake word events generated

---

# Language Tests

[ ] English supported

[ ] Amharic supported

[ ] Arabic supported

[ ] Language selection updates context

---

# Whisper Tests

[ ] Whisper loads successfully

[ ] Whisper loads only once

[ ] Speech transcribes correctly

[ ] Language detection works

---

# Scenario Engine Tests

[ ] Scenario file loads

[ ] Scenario validation works

[ ] Text normalization works

[ ] Exact matching works

[ ] Keyword matching works

[ ] Fallback works

---

# Playback Tests

[ ] WAV playback works

[ ] MP3 playback works

[ ] Playback state tracked

[ ] Playback position tracked

---

# VAD Tests

[ ] Speech detected

[ ] Silence detected

[ ] Interruption detected

[ ] Interruption event generated

---

# Interruption Tests

[ ] Response pauses

[ ] Interruption audio plays

[ ] Silence resumes playback

[ ] Playback continues from previous position

---

# FSM Tests

[ ] IDLE works

[ ] FACE_RECOGNIZED works

[ ] GREETING works

[ ] WAITING_FOR_WAKE_WORD works

[ ] CONVERSATION_ACTIVE works

[ ] PLAYING_AUDIO works

[ ] INTERRUPTED works

[ ] TIMEOUT works

[ ] RETURN_TO_IDLE works

[ ] Invalid transitions rejected

[ ] State transitions logged

---

# Dashboard Tests

[ ] Dashboard loads

[ ] Webcam feed visible

[ ] Logs visible

[ ] Status cards visible

[ ] System state visible

---

# Scenario Management Tests

[ ] Scenario creation works

[ ] Scenario editing works

[ ] Scenario deletion works

[ ] Audio upload works

---

# Settings Tests

[ ] Settings load

[ ] Settings save

[ ] Whisper model changes persist

[ ] VAD settings persist

---

# End-To-End Demonstration Tests

[ ] User enrolled

[ ] User recognized

[ ] Greeting plays

[ ] Wake word detected

[ ] Language selected

[ ] Question asked

[ ] Scenario matched

[ ] Response played

[ ] Interruption detected

[ ] Interruption response played

[ ] Original playback resumed

[ ] Timeout occurs

[ ] Return to idle

---

# Final Acceptance

Project is accepted only when ALL checkboxes pass.

No TODOs.

No placeholders.

No mock implementations.

No incomplete workflows.

The complete demonstration must execute successfully from beginning to end.