# STATE_MACHINE_V3.md

# EthioChatbot V3
## State Machine Specification

---

# Document Purpose

This document defines the official Finite State Machine (FSM) for EthioChatbot V3.

The FSM governs:

- System behavior
- User recognition flow
- Greeting execution
- Dialog execution
- Face presence tracking
- Monitoring behavior
- Playback interruption handling

This document is the authoritative reference for all state transitions.

---

# FSM Design Principles

The state machine shall be:

- Deterministic
- Event-driven
- Offline-only
- Easy to debug
- Easy to extend

The FSM shall never:

- Perform face recognition directly
- Perform playback directly
- Contain UI logic
- Contain camera logic

The FSM only manages system states and transitions.

---

# State Overview

EthioChatbot V3 contains the following states:

```text
FACE_DETECTION_MODE

FACE_DETECTED

FACE_RECOGNIZED

PRIORITY_SORTING

GREETING_QUEUE

PLAY_GREETINGS

PLAY_COMMON_DIALOG

PLAY_USER_DIALOGS

PAUSED_DIALOG

MONITORING
```

---

# State Definitions

---

# STATE: FACE_DETECTION_MODE

Purpose:

```text
Default operational state.

Continuously monitor camera feed
for faces.
```

Entry Conditions:

```text
System startup

OR

ALL_USERS_LOST
```

Allowed Events:

```text
FACE_DETECTED
```

Transition:

```text
FACE_DETECTION_MODE
↓ FACE_DETECTED
FACE_DETECTED
```

---

# STATE: FACE_DETECTED

Purpose:

```text
One or more faces have been detected.

Recognition has not yet been completed.
```

Allowed Events:

```text
FACE_RECOGNIZED
NO_FACE_FOUND
```

Transitions:

```text
FACE_DETECTED
↓ FACE_RECOGNIZED
FACE_RECOGNIZED
```

```text
FACE_DETECTED
↓ NO_FACE_FOUND
FACE_DETECTION_MODE
```

---

# STATE: FACE_RECOGNIZED

Purpose:

```text
One or more enrolled users
have been successfully recognized.
```

Responsibilities:

```text
Build recognized user list
```

Allowed Events:

```text
RECOGNITION_COMPLETE
```

Transition:

```text
FACE_RECOGNIZED
↓ RECOGNITION_COMPLETE
PRIORITY_SORTING
```

---

# STATE: PRIORITY_SORTING

Purpose:

```text
Sort recognized users
according to priority.
```

Priority Rule:

```text
Lower Number
=
Higher Priority
```

Example:

```text
Manager (1)

Natnael (2)

Visitor (3)
```

Sorted Result:

```text
Manager
↓
Natnael
↓
Visitor
```

Allowed Events:

```text
SORTING_COMPLETE
```

Transition:

```text
PRIORITY_SORTING
↓ SORTING_COMPLETE
GREETING_QUEUE
```

---

# STATE: GREETING_QUEUE

Purpose:

```text
Create greeting queue.
```

Queue Examples:

## Single User

```text
Natnael
```

## Multiple Users

```text
Manager
↓
Natnael
↓
Visitor
```

Allowed Events:

```text
QUEUE_READY
```

Transition:

```text
GREETING_QUEUE
↓ QUEUE_READY
PLAY_GREETINGS
```

---

# STATE: PLAY_GREETINGS

Purpose:

```text
Play greeting audio
for all users in queue.
```

Rules:

```text
One greeting at a time.

No overlapping playback.

Priority order must be respected.
```

Example:

```text
manager.wav
↓
natnael.wav
↓
visitor.wav
```

Allowed Events:

```text
ALL_GREETINGS_FINISHED
```

Transitions:

## Mode A

```text
PLAY_GREETINGS
↓ ALL_GREETINGS_FINISHED
PLAY_COMMON_DIALOG
```

## Mode B

```text
PLAY_GREETINGS
↓ ALL_GREETINGS_FINISHED
PLAY_USER_DIALOGS
```

---

# STATE: PLAY_COMMON_DIALOG

Purpose:

```text
Mode A playback state.
```

Definition:

```text
Play a single common dialog
after all greetings finish.
```

Example:

```text
Manager Greeting
↓
Natnael Greeting
↓
Visitor Greeting
↓
Common Dialog
```

Allowed Events:

```text
COMMON_DIALOG_FINISHED

INTERRUPT_DIALOG
```

Transitions:

```text
PLAY_COMMON_DIALOG
↓ COMMON_DIALOG_FINISHED
MONITORING
```

```text
PLAY_COMMON_DIALOG
↓ INTERRUPT_DIALOG
PAUSED_DIALOG
```

---

# STATE: PLAY_USER_DIALOGS

Purpose:

```text
Mode B playback state.
```

Definition:

```text
Play user-specific
dialog audio.
```

Example:

```text
Manager Greeting
↓
Manager Dialog

↓

Natnael Greeting
↓
Natnael Dialog
```

Allowed Events:

```text
USER_DIALOGS_FINISHED

INTERRUPT_DIALOG
```

Transitions:

```text
PLAY_USER_DIALOGS
↓ USER_DIALOGS_FINISHED
MONITORING
```

```text
PLAY_USER_DIALOGS
↓ INTERRUPT_DIALOG
PAUSED_DIALOG
```

---

# STATE: PAUSED_DIALOG

Purpose:

```text
Temporarily pause
dialog playback.
```

Scope:

```text
Dialog audio only.

Greeting audio
cannot be interrupted.
```

Requirements:

```text
Save playback position.

Resume from same position.
```

Allowed Events:

```text
RESUME_DIALOG
```

Transitions:

If interrupted from:

```text
PLAY_COMMON_DIALOG
```

then:

```text
PAUSED_DIALOG
↓ RESUME_DIALOG
PLAY_COMMON_DIALOG
```

If interrupted from:

```text
PLAY_USER_DIALOGS
```

then:

```text
PAUSED_DIALOG
↓ RESUME_DIALOG
PLAY_USER_DIALOGS
```

---

# STATE: MONITORING

Purpose:

```text
System remains active.

Track visible users.

Monitor face presence.

Do not replay greetings.
```

Responsibilities:

```text
Maintain active user list.

Track face persistence.

Wait for departures
and new arrivals.
```

Allowed Events:

```text
NEW_USER_DETECTED

FACE_LOST

ALL_USERS_LOST
```

Transitions:

## New User

```text
MONITORING
↓ NEW_USER_DETECTED
FACE_RECOGNIZED
```

---

## User Leaves

```text
MONITORING
↓ FACE_LOST
MONITORING
```

Remain in monitoring mode.

---

## All Users Leave

```text
MONITORING
↓ ALL_USERS_LOST
FACE_DETECTION_MODE
```

---

# Face Presence Workflow

Configuration:

```json
{
  "face_lost_timeout": 5
}
```

Workflow:

```text
Face disappears
↓
Start timer
↓
5 seconds pass
↓
FACE_LOST
```

---

# Temporary Face Loss

```text
Face disappears
↓
Returns before timeout
```

Result:

```text
Cancel loss timer
```

No event generated.

---

# Greeting Persistence Rules

A user may only be greeted once per presence session.

Example:

```text
User arrives
↓
Greeting played
↓
User remains visible
```

Result:

```text
No replay.
```

---

# Re-Greeting Conditions

Greetings may be replayed only if:

```text
FACE_LOST occurred
AND
User reappears
```

Example:

```text
User leaves
↓
FACE_LOST
↓
User returns
↓
New Greeting Session
```

---

# Interaction Mode Selection

Source:

```json
{
  "interaction_mode": "common_dialog"
}
```

Possible values:

```text
common_dialog

user_specific_dialog
```

---

# Mode A Flow

```text
FACE_RECOGNIZED
↓
PRIORITY_SORTING
↓
GREETING_QUEUE
↓
PLAY_GREETINGS
↓
PLAY_COMMON_DIALOG
↓
MONITORING
```

---

# Mode B Flow

```text
FACE_RECOGNIZED
↓
PRIORITY_SORTING
↓
GREETING_QUEUE
↓
PLAY_GREETINGS
↓
PLAY_USER_DIALOGS
↓
MONITORING
```

---

# Complete FSM Diagram

```text
FACE_DETECTION_MODE
↓
FACE_DETECTED
↓
FACE_RECOGNIZED
↓
PRIORITY_SORTING
↓
GREETING_QUEUE
↓
PLAY_GREETINGS

Mode A
↓
PLAY_COMMON_DIALOG

Mode B
↓
PLAY_USER_DIALOGS

↓

MONITORING

↓

ALL_USERS_LOST

↓

FACE_DETECTION_MODE
```

---

# State Transition Rules

The FSM shall:

✅ Allow only valid transitions.

✅ Reject invalid state changes.

✅ Log every transition.

✅ Maintain current state centrally.

✅ Publish state change events.

The FSM shall not:

❌ Execute recognition logic.

❌ Execute playback logic.

❌ Execute dashboard logic.

❌ Execute enrollment logic.

---

# End of Document
