# EthioChatbot V2 State Machine Specification

## Purpose

This document defines the Finite State Machine (FSM) that controls EthioChatbot V2.

The FSM is the authoritative controller of robot behavior.

All robot actions must occur through valid state transitions.

The FSM coordinates:

- Face Detection
- Face Recognition
- Priority Based Greetings
- Wake Word Detection
- Conversation Activation
- Audio Playback
- Interruption Handling
- Timeout Handling
- Face Persistence
- Idle State Management

The FSM must remain simple, deterministic, and suitable for implementation within five hours.

---

# FSM Principles

## Principle 1

All state transitions are event-driven.

States must never be changed directly.

---

## Principle 2

Every transition must be validated.

Invalid transitions must be:

- Rejected
- Logged

---

## Principle 3

Every transition must be logged.

Examples:

FACE_DETECTED

FACE_RECOGNIZED

WAKE_WORD_DETECTED

PLAYBACK_STARTED

TIMEOUT_OCCURRED

FACE_LOST

---

## Principle 4

The FSM is responsible for all conversation workflow control.

No service may bypass the FSM.

---

## Principle 5

The robot remains active while recognized users remain visible.

The robot returns to IDLE only when all recognized users leave the camera view.

---

# State List

## IDLE

Default robot state.

No enrolled users are currently recognized.

System Behavior:

- Camera Monitoring Active
- Face Detection Active
- Face Recognition Active
- Microphone Passive
- No Active Conversation

Entry Conditions:

- Application startup completed
- All recognized users lost
- Return to idle completed

Exit Conditions:

- Face detected

---

## FACE_DETECTED

A face has been detected in the camera stream.

Recognition has not yet been completed.

System Behavior:

- Evaluate face
- Generate embeddings
- Attempt recognition

Entry Conditions:

- FACE_DETECTED Event

Exit Conditions:

- Recognition succeeds
- Recognition fails

---

## FACE_RECOGNIZED

One or more enrolled users have been recognized.

System Behavior:

- Load recognized users
- Load priorities
- Sort users

Entry Conditions:

- FACE_RECOGNIZED Event

Exit Conditions:

- Greeting begins

---

## PRIORITY_SORTING

Recognized users are sorted by priority.

Priority Rules:

Lower Number = Higher Priority

Example:

Priority 1

↓

Priority 2

↓

Priority 3

System Behavior:

- Sort users
- Build greeting queue

Entry Conditions:

- Users recognized

Exit Conditions:

- Greeting queue created

---

## GREETING

The robot is greeting recognized users.

Greeting Rules:

- Greeting language is English
- Greeting order follows priority
- One greeting at a time

Example:

Hello Manager.

↓

Hello Natnael.

↓

Hello Visitor.

Entry Conditions:

- Greeting queue ready

Exit Conditions:

- All greetings completed

---

## WAITING_FOR_WAKE_WORD

The robot is listening for wake words.

System Behavior:

- Microphone active
- VAD active
- Wake word detection active
- Face monitoring active

This state persists while recognized users remain visible.

Entry Conditions:

- Greetings complete
- Conversation timeout
- Conversation finished

Exit Conditions:

- Wake word detected
- All faces lost

---

## CONVERSATION_ACTIVE

User conversation is active.

System Behavior:

- Speech recognition active
- Scenario matching active
- Language context active

Entry Conditions:

- Wake word detected

Exit Conditions:

- Audio playback required
- Conversation timeout

---

## PLAYING_AUDIO

Robot response audio is playing.

System Behavior:

- Playback active
- VAD monitoring active

Entry Conditions:

- Matching scenario found
- Playback started

Exit Conditions:

- Playback finished
- User interruption

---

## INTERRUPTED

User interrupted active playback.

System Behavior:

- Pause current playback
- Play interruption audio
- Wait for silence

Example:

please_wait.wav

Entry Conditions:

- INTERRUPTION_DETECTED Event

Exit Conditions:

- Silence detected

---

## TIMEOUT

Conversation timeout occurred.

System Behavior:

- Clear conversation context
- Clear language context

Entry Conditions:

- Timeout event

Exit Conditions:

- Determine next state

---

## FACE_LOST_CHECK

This state evaluates active users after timeout or face disappearance.

System Behavior:

- Check active users
- Check face persistence timers

Entry Conditions:

- TIMEOUT completed
- FACE_LOST event

Exit Conditions:

- Users remain
- No users remain

---

## RETURN_TO_IDLE

System cleanup state.

System Behavior:

- Clear active users
- Reset session state
- Reset language context
- Reset playback state

Entry Conditions:

- No active users remain

Exit Conditions:

- IDLE

---

# State Transition Diagram

IDLE

↓

FACE_DETECTED

↓

FACE_RECOGNIZED

↓

PRIORITY_SORTING

↓

GREETING

↓

WAITING_FOR_WAKE_WORD

↓

CONVERSATION_ACTIVE

↓

PLAYING_AUDIO

↓

CONVERSATION_ACTIVE

↓

PLAYING_AUDIO

↓

CONVERSATION_ACTIVE

↓

TIMEOUT

↓

FACE_LOST_CHECK

↓

WAITING_FOR_WAKE_WORD

OR

RETURN_TO_IDLE

↓

IDLE

---

# Greeting Workflow

IDLE

↓

FACE_DETECTED

↓

FACE_RECOGNIZED

↓

PRIORITY_SORTING

↓

GREETING

↓

WAITING_FOR_WAKE_WORD

Rules:

- Greeting always uses English
- Greeting follows priority order
- Greeting only happens once per detection cycle

---

# Wake Word Workflow

WAITING_FOR_WAKE_WORD

↓

WAKE_WORD_DETECTED

↓

CONVERSATION_ACTIVE

Wake words determine conversation language.

Examples:

Hello Robot

↓

English

ሰላም ሮቦት

↓

Amharic

مرحبا روبوت

↓

Arabic

---

# Conversation Workflow

WAITING_FOR_WAKE_WORD

↓

CONVERSATION_ACTIVE

↓

PLAYING_AUDIO

↓

CONVERSATION_ACTIVE

↓

PLAYING_AUDIO

↓

CONVERSATION_ACTIVE

The conversation continues until timeout.

---

# Language Context Rules

Language is determined once per session.

Priority:

1. Wake Word Language
2. User Preferred Language
3. English

Store:

current_language

Language remains active during:

CONVERSATION_ACTIVE

PLAYING_AUDIO

INTERRUPTED

Language context is cleared during:

TIMEOUT

RETURN_TO_IDLE

---

# Interruption Workflow

PLAYING_AUDIO

↓

INTERRUPTED

↓

PLAYING_AUDIO

Behavior:

Pause current audio

↓

Play interruption audio

↓

Wait for silence

↓

Resume original audio

Requirements:

- Resume original playback position
- Do not restart playback

---

# Timeout Workflow

CONVERSATION_ACTIVE

↓

TIMEOUT

↓

FACE_LOST_CHECK

↓

WAITING_FOR_WAKE_WORD

or

RETURN_TO_IDLE

---

# Face Persistence Workflow

Recognized users maintain:

last_seen timestamp

When user remains visible:

last_seen updated

When user disappears:

last_seen stops updating

Recommended timeout:

5 seconds

After timeout:

FACE_LOST Event

---

# Face Lost Workflow

One User Leaves

↓

Other Users Still Visible

↓

WAITING_FOR_WAKE_WORD

No return to idle.

---

All Users Leave

↓

FACE_LOST_CHECK

↓

RETURN_TO_IDLE

↓

IDLE

---

# Invalid Transitions

Examples:

IDLE

↓

PLAYING_AUDIO

Invalid

---

GREETING

↓

INTERRUPTED

Invalid

---

PLAYING_AUDIO

↓

IDLE

Invalid

---

Invalid transitions must:

- Be rejected
- Be logged

---

# Event Ownership

Typical Events:

FACE_DETECTED

→ FACE_DETECTED

FACE_RECOGNIZED

→ FACE_RECOGNIZED

GREETING_FINISHED

→ WAITING_FOR_WAKE_WORD

WAKE_WORD_DETECTED

→ CONVERSATION_ACTIVE

SCENARIO_MATCHED

→ PLAYING_AUDIO

INTERRUPTION_DETECTED

→ INTERRUPTED

INTERRUPTION_CLEARED

→ PLAYING_AUDIO

TIMEOUT_OCCURRED

→ TIMEOUT

FACE_LOST

→ FACE_LOST_CHECK

NO_ACTIVE_USERS

→ RETURN_TO_IDLE

RETURN_TO_IDLE_COMPLETE

→ IDLE

---

# Raspberry Pi Optimization Rules

The FSM must remain lightweight.

Avoid:

- Complex nested states
- Recursive transitions
- Long-lived state objects

Store only:

- Current State
- Current Language
- Active Users
- Timeout Information

FSM decisions must remain fast and deterministic.

---

# Demonstration Success Criteria

The FSM is considered complete when:

✓ Face detection transitions work

✓ Face recognition transitions work

✓ Priority sorting works

✓ Sequential greetings work

✓ Wake word detection works

✓ English sessions work

✓ Amharic sessions work

✓ Arabic sessions work

✓ Audio playback works

✓ Interruption handling works

✓ Playback resumption works

✓ Timeout works

✓ Face persistence works

✓ Face lost detection works

✓ WAITING_FOR_WAKE_WORD persists while users remain visible

✓ IDLE occurs only when all users leave

✓ Full demonstration workflow succeeds

The FSM is the authoritative behavioral model for EthioChatbot V2.
