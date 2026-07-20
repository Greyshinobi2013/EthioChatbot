# STATE_MACHINE_V3.md

# EthioChatbot V3
## Finite State Machine Specification

---

# Document Purpose

This document defines the official Finite State Machine (FSM) for EthioChatbot V3.

The FSM controls:

- Face detection workflow
- Face recognition workflow
- User tracking
- Priority sorting
- Greeting execution
- Dialog playback
- Head motion behavior
- Presence monitoring
- Dialog interruption handling

This FSM is the authoritative source for all state transitions.

---

# Design Principles

The FSM shall be:

```text
Deterministic

Event Driven

Offline

Predictable

Easy To Debug

Easy To Maintain
```

The FSM shall never:

```text
Perform Face Recognition

Perform Audio Playback

Perform Servo Control

Access Dashboard Logic
```

These actions are performed by services.

The FSM only controls:

```text
States

Transitions

State Actions

Workflow Progression
```

---

# State Overview

EthioChatbot V3 consists of the following states:

```text
SYSTEM_STARTUP

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

# Complete FSM Diagram

```text
SYSTEM_STARTUP
↓
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

# STATE: SYSTEM_STARTUP

Purpose:

```text
Initialize all system components.
```

Responsibilities:

```text
Load Configuration

Initialize Camera

Initialize Face Recognition

Initialize Event Bus

Initialize FSM

Initialize Playback Service

Initialize Head Motion Controller
```

Entry Actions:

```text
System Initialization
```

Allowed Events:

```text
STARTUP_COMPLETE
```

Transition:

```text
SYSTEM_STARTUP
↓
STARTUP_COMPLETE
↓
FACE_DETECTION_MODE
```

---

# STATE: FACE_DETECTION_MODE

Purpose:

```text
Default operating state.
```

Responsibilities:

```text
Monitor environment

Search for users

Scan surroundings
```

Entry Actions:

```text
Start Surveillance Scan
```

Head Motion:

```text
Yaw:
    Active Scan

Pitch:
    Neutral
```

Yaw Pattern:

```text
Left
↓
Center
↓
Right
↓
Center
```

Allowed Events:

```text
FACE_DETECTED
```

Transition:

```text
FACE_DETECTION_MODE
↓
FACE_DETECTED
↓
FACE_DETECTED
```

---

# STATE: FACE_DETECTED

Purpose:

```text
One or more faces have been detected.
```

Responsibilities:

```text
Stop scanning

Start face tracking

Prepare recognition
```

Entry Actions:

```text
Stop Surveillance Scan

Start Face Tracking
```

Head Motion:

```text
Yaw:
    Track Face

Pitch:
    Neutral
```

Allowed Events:

```text
FACE_RECOGNIZED

NO_FACE_FOUND
```

Transitions:

```text
FACE_DETECTED
↓
FACE_RECOGNIZED
↓
FACE_RECOGNIZED
```

```text
FACE_DETECTED
↓
NO_FACE_FOUND
↓
FACE_DETECTION_MODE
```

---

# STATE: FACE_RECOGNIZED

Purpose:

```text
Recognized users are available.
```

Responsibilities:

```text
Create recognized user list

Prepare sorting phase
```

Head Motion:

```text
Yaw:
    Continue Tracking

Pitch:
    Neutral
```

Allowed Events:

```text
RECOGNITION_COMPLETE
```

Transition:

```text
FACE_RECOGNIZED
↓
RECOGNITION_COMPLETE
↓
PRIORITY_SORTING
```

---

# STATE: PRIORITY_SORTING

Purpose:

```text
Sort recognized users.
```

Rule:

```text
Lower Priority Number
=
Higher Priority
```

Example:

```text
Manager    Priority 1

Natnael    Priority 2

Visitor    Priority 3
```

Result:

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
↓
SORTING_COMPLETE
↓
GREETING_QUEUE
```

---

# STATE: GREETING_QUEUE

Purpose:

```text
Generate playback queue.
```

Responsibilities:

```text
Build greeting order

Apply interaction mode logic
```

Examples:

Single User:

```text
Natnael
```

Multiple Users:

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
↓
QUEUE_READY
↓
PLAY_GREETINGS
```

---

# STATE: PLAY_GREETINGS

Purpose:

```text
Execute greeting sequence.
```

Responsibilities:

```text
Play Greeting Audio

Perform Greeting Nods
```

Entry Actions:

```text
Start Greeting Playback

Start Greeting Nod
```

Head Motion:

```text
Yaw:
    Face Tracking Active

Pitch:
    Greeting Nodding Active
```

Pitch Nodding Pattern:

```text
Center
↓
Down
↓
Center
↓
Down
↓
Center
```

Rules:

```text
Every Greeting
=
One Nod Sequence

Greetings are played sequentially.

No overlapping greetings allowed.
```

Allowed Events:

```text
ALL_GREETINGS_FINISHED
```

Transitions:

Mode A:

```text
PLAY_GREETINGS
↓
ALL_GREETINGS_FINISHED
↓
PLAY_COMMON_DIALOG
```

Mode B:

```text
PLAY_GREETINGS
↓
ALL_GREETINGS_FINISHED
↓
PLAY_USER_DIALOGS
```

---

# STATE: PLAY_COMMON_DIALOG

Purpose:

```text
Mode A dialog playback.
```

Definition:

```text
Play one common dialog
after all greetings finish.
```

Example:

```text
Manager Greeting + Nod
↓
Natnael Greeting + Nod
↓
Visitor Greeting + Nod
↓
Common Dialog
```

Head Motion:

```text
Yaw:
    Track Active User

Pitch:
    Neutral
```

Allowed Events:

```text
COMMON_DIALOG_FINISHED

INTERRUPT_DIALOG
```

Transitions:

```text
PLAY_COMMON_DIALOG
↓
COMMON_DIALOG_FINISHED
↓
MONITORING
```

```text
PLAY_COMMON_DIALOG
↓
INTERRUPT_DIALOG
↓
PAUSED_DIALOG
```

---

# STATE: PLAY_USER_DIALOGS

Purpose:

```text
Mode B dialog playback.
```

Definition:

```text
Play user-specific dialog audio.
```

Example:

```text
Manager Greeting + Nod
↓
Manager Dialog

↓

Natnael Greeting + Nod
↓
Natnael Dialog
```

Head Motion:

```text
Yaw:
    Track Active User

Pitch:
    Neutral
```

Allowed Events:

```text
USER_DIALOGS_FINISHED

INTERRUPT_DIALOG
```

Transitions:

```text
PLAY_USER_DIALOGS
↓
USER_DIALOGS_FINISHED
↓
MONITORING
```

```text
PLAY_USER_DIALOGS
↓
INTERRUPT_DIALOG
↓
PAUSED_DIALOG
```

---

# STATE: PAUSED_DIALOG

Purpose:

```text
Temporary dialog interruption.
```

Responsibilities:

```text
Preserve Playback Position

Wait For Resume
```

Head Motion:

```text
Yaw:
    Continue Tracking

Pitch:
    Neutral
```

Allowed Events:

```text
RESUME_DIALOG

RESTART_GREETINGS
```

Transition:

Resume:

```text
PAUSED_DIALOG
↓
RESUME_DIALOG
↓
Return To Previous Dialog State
```

Restart:

```text
PAUSED_DIALOG
↓
RESTART_GREETINGS
↓
GREETING_QUEUE
```

Requirements:

```text
Resume must continue from
previous playback position.

Restart Greetings must create
an entirely new interaction cycle.
```

---

# STATE: MONITORING

Purpose:

```text
Observe active users.

Track presence.

Await departures and arrivals.
```

Responsibilities:

```text
Face Tracking

Presence Monitoring

User Tracking
```

Head Motion:

```text
Yaw:
    Track Highest Priority User

Pitch:
    Neutral
```

No greetings or dialogs are played in this state.

Allowed Events:

```text
NEW_USER_DETECTED

FACE_LOST

ALL_USERS_LOST

RESTART_GREETINGS
```

Transitions:

New User:

```text
MONITORING
↓
NEW_USER_DETECTED
↓
FACE_RECOGNIZED
```

Face Lost:

```text
MONITORING
↓
FACE_LOST
↓
MONITORING
```

All Users Lost:

```text
MONITORING
↓
ALL_USERS_LOST
↓
FACE_DETECTION_MODE
```

Restart Greetings:

```text
MONITORING
↓
RESTART_GREETINGS
↓
GREETING_QUEUE
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
Face Disappears
↓
Start Timer
↓
5 Seconds
↓
FACE_LOST
```

---

# Temporary Face Loss

```text
Face Disappears
↓
User Returns Before Timeout
```

Result:

```text
Cancel Timeout

Remain Active
```

No greeting replay.

---

# Greeting Persistence Rules

Users shall only be greeted once per presence session.

Example:

```text
User Appears
↓
Greeting Completed
↓
User Remains Visible
```

Result:

```text
No Additional Greeting
```

---

# Re-Greeting Conditions

Greetings may replay only if:

```text
FACE_LOST occurred
AND
User Returns
```

Example:

```text
User Leaves
↓
FACE_LOST
↓
User Returns
↓
New Greeting Session
```

---

# Interaction Modes

Configuration Source:

```json
{
  "interaction_mode": "common_dialog"
}
```

Allowed Values:

```text
common_dialog

user_specific_dialog
```

---

# Mode A FSM Path

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

# Mode B FSM Path

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

# Head Motion State Summary

| State | Yaw | Pitch |
|---------|---------|---------|
| FACE_DETECTION_MODE | Surveillance Scan | Neutral |
| FACE_DETECTED | Track Face | Neutral |
| FACE_RECOGNIZED | Track Face | Neutral |
| PRIORITY_SORTING | Track Face | Neutral |
| GREETING_QUEUE | Track Face | Neutral |
| PLAY_GREETINGS | Track Face | Greeting Nod |
| PLAY_COMMON_DIALOG | Track Face | Neutral |
| PLAY_USER_DIALOGS | Track Face | Neutral |
| PAUSED_DIALOG | Track Face | Neutral |
| MONITORING | Track Highest Priority User | Neutral |

---

# FSM Rules

The FSM shall:

✅ Validate all transitions

✅ Log all transitions

✅ Reject invalid transitions

✅ Publish state-change events

✅ Follow documented workflows

The FSM shall not:

❌ Perform recognition

❌ Perform playback

❌ Perform servo control

❌ Perform dashboard actions

---

# End of Document
