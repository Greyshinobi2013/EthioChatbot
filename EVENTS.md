# Event Specification

## Purpose

The robot uses an event-driven architecture.

Events coordinate communication between services.

Services do not directly control each other.

Services communicate through the Event Bus.

---

# Event Bus

Implementation:

utils/event_bus.py

Responsibilities:

- Publish events
- Subscribe handlers
- Route events
- Dispatch callbacks

Requirements:

- Thread-safe
- Lightweight
- Local process only

Do not use:

- RabbitMQ
- Kafka
- Redis Pub/Sub

A simple in-process implementation is sufficient.

---

# Face Events

FACE_DETECTED

Description:

A face has been detected.

FACE_RECOGNIZED

Description:

An enrolled user was identified.

FACE_UNKNOWN

Description:

Face detected but not recognized.

FACE_LOST

Description:

Previously detected face is no longer visible.

---

# Greeting Events

GREETING_STARTED

Description:

Greeting playback started.

GREETING_FINISHED

Description:

Greeting playback finished.

---

# Wake Word Events

WAKE_WORD_DETECTED

Description:

Valid wake word detected.

WAKE_WORD_REJECTED

Description:

Speech detected but no valid wake word found.

---

# Language Events

LANGUAGE_SELECTED

Description:

Conversation language selected.

LANGUAGE_CHANGED

Description:

Language switched during session.

---

# Speech Events

SPEECH_DETECTED

Description:

Speech activity detected.

TRANSCRIPTION_STARTED

Description:

Whisper transcription started.

TRANSCRIPTION_READY

Description:

Transcription completed.

---

# Scenario Events

SCENARIO_MATCHED

Description:

Matching scenario found.

SCENARIO_NOT_FOUND

Description:

No matching scenario available.

---

# Playback Events

PLAYBACK_STARTED

Description:

Audio playback started.

PLAYBACK_PAUSED

Description:

Audio playback paused.

PLAYBACK_RESUMED

Description:

Audio playback resumed.

PLAYBACK_STOPPED

Description:

Playback stopped.

PLAYBACK_FINISHED

Description:

Playback completed.

---

# Interruption Events

INTERRUPTION_DETECTED

Description:

User speech interrupted playback.

INTERRUPTION_CLEARED

Description:

Silence detected after interruption.

---

# System Events

SYSTEM_STARTUP

Description:

Application startup complete.

SYSTEM_SHUTDOWN

Description:

Application shutdown initiated.

ERROR_OCCURRED

Description:

Unhandled error detected.

TIMEOUT_OCCURRED

Description:

Conversation timeout reached.

RETURN_TO_IDLE

Description:

System returning to idle state.

---

# Event Rules

All state transitions occur through events.

State changes without events are prohibited.

Services communicate via the Event Bus.

Events must be logged whenever practical.

---

# Demonstration Requirements

The event system is complete when:

✓ Events can be published

✓ Events can be subscribed

✓ Events are received correctly

✓ FSM reacts to events

✓ Services communicate through events

✓ Event-based workflow works end-to-end