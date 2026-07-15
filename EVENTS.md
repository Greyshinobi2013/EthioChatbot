# Event Definitions

The application uses an event-driven architecture.

---

## Face Events

FACE_DETECTED

FACE_RECOGNIZED

FACE_UNKNOWN

FACE_LOST

---

## Greeting Events

GREETING_STARTED

GREETING_FINISHED

---

## Wake Word Events

WAKE_WORD_DETECTED

WAKE_WORD_REJECTED

---

## Language Events

LANGUAGE_SELECTED

LANGUAGE_CHANGED

---

## Speech Events

SPEECH_DETECTED

TRANSCRIPTION_STARTED

TRANSCRIPTION_READY

---

## Scenario Events

SCENARIO_MATCHED

SCENARIO_NOT_FOUND

---

## Playback Events

PLAYBACK_STARTED

PLAYBACK_PAUSED

PLAYBACK_RESUMED

PLAYBACK_STOPPED

PLAYBACK_FINISHED

---

## Interruption Events

INTERRUPTION_DETECTED

INTERRUPTION_CLEARED

---

## System Events

TIMEOUT_OCCURRED

RETURN_TO_IDLE

ERROR_OCCURRED

SYSTEM_STARTUP

SYSTEM_SHUTDOWN

---

## Rules

Events are the only mechanism for changing state.

Services communicate through events.

Services must not directly call internal state transitions.