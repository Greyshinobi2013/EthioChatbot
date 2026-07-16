# State Machine Specification

## Purpose

The robot is controlled by a finite state machine.

The FSM coordinates the entire conversation lifecycle.

All state transitions must be logged.

The FSM must remain simple enough to be implemented within one working day.

---

# FSM Rules

State transitions occur only through events.

Direct state manipulation is prohibited.

All transitions must be validated.

Invalid transitions must generate warnings.

---

# States

## IDLE

Default robot state.

The robot waits for a recognized user.

---

## FACE_ENROLLMENT

User enrollment process.

Capturing and storing face data.

---

## FACE_DETECTED

A face has been detected.

Recognition pending.

---

## FACE_RECOGNIZED

Enrolled user successfully identified.

---

## GREETING

Greeting audio is playing.

---

## WAITING_FOR_WAKE_WORD

Robot is waiting for a valid wake word.

---

## LANGUAGE_SELECTION

Language selection process.

---

## CONVERSATION_ACTIVE

Conversation session active.

Robot accepts user questions.

---

## PLAYING_AUDIO

Response audio currently playing.

---

## INTERRUPTED

User interrupted playback.

Playback paused.

Interruption audio playing.

---

## TIMEOUT

Conversation inactivity timeout reached.

---

## RETURN_TO_IDLE

Cleanup state before returning to idle.

---

# State Transition Diagram

IDLE
↓
FACE_DETECTED

FACE_DETECTED
↓
FACE_RECOGNIZED

FACE_RECOGNIZED
↓
GREETING

GREETING
↓
WAITING_FOR_WAKE_WORD

WAITING_FOR_WAKE_WORD
↓
LANGUAGE_SELECTION

LANGUAGE_SELECTION
↓
CONVERSATION_ACTIVE

CONVERSATION_ACTIVE
↓
PLAYING_AUDIO

PLAYING_AUDIO
↓
INTERRUPTED

INTERRUPTED
↓
PLAYING_AUDIO

CONVERSATION_ACTIVE
↓
TIMEOUT

TIMEOUT
↓
RETURN_TO_IDLE

RETURN_TO_IDLE
↓
IDLE

---

# Greeting Workflow

FACE_RECOGNIZED

↓

GREETING

↓

WAITING_FOR_WAKE_WORD

The greeting must occur automatically.

No user interaction required.

---

# Conversation Workflow

WAITING_FOR_WAKE_WORD

↓

LANGUAGE_SELECTION

↓

CONVERSATION_ACTIVE

↓

PLAYING_AUDIO

↓

CONVERSATION_ACTIVE

The conversation continues until timeout.

---

# Interruption Workflow

PLAYING_AUDIO

↓

INTERRUPTED

↓

PLAYING_AUDIO

Audio resumes from the previous position.

Audio must not restart.

---

# Timeout Workflow

CONVERSATION_ACTIVE

↓

TIMEOUT

↓

RETURN_TO_IDLE

↓

IDLE

The robot returns to listening mode.

---

# Invalid Transition Examples

Invalid:

IDLE
↓
PLAYING_AUDIO

Invalid:

GREETING
↓
TIMEOUT

Invalid transitions must:

- Be rejected
- Be logged

---

# Event Ownership

Typical triggering events:

FACE_DETECTED
→ FACE_DETECTED State

FACE_RECOGNIZED
→ FACE_RECOGNIZED State

GREETING_FINISHED
→ WAITING_FOR_WAKE_WORD

WAKE_WORD_DETECTED
→ LANGUAGE_SELECTION

LANGUAGE_SELECTED
→ CONVERSATION_ACTIVE

PLAYBACK_STARTED
→ PLAYING_AUDIO

INTERRUPTION_DETECTED
→ INTERRUPTED

INTERRUPTION_CLEARED
→ PLAYING_AUDIO

TIMEOUT_OCCURRED
→ TIMEOUT

RETURN_TO_IDLE
→ IDLE

---

# Demonstration Requirements

The FSM is complete when:

✓ All states exist

✓ All transitions work

✓ Invalid transitions are rejected

✓ Transitions are logged

✓ Interruption workflow works

✓ Timeout workflow works

✓ Full conversation workflow succeeds

The FSM must successfully support the complete demonstration workflow.