# SYSTEM_ARCHITECTURE_V3.md

# EthioChatbot V3
## System Architecture Specification

---

# Document Purpose

This document defines the complete system architecture for EthioChatbot V3.

The architecture describes:

- System components
- Component responsibilities
- Component interactions
- Data flow
- Technology stack
- Runtime behavior
- Deployment architecture

This document is the authoritative reference for implementation.

---

# 1. Architecture Overview

EthioChatbot V3 is an offline face-recognition-based multilingual greeting and information system.

The system continuously monitors a camera feed, detects registered users, recognizes them, prioritizes greetings, and plays pre-recorded audio interactions.

The architecture is intentionally simple and optimized for:

```text
Raspberry Pi 4
8GB RAM
32GB Storage
1.8GHz CPU
```

---

# 2. Architectural Principles

The system shall follow the following principles:

### Offline First

All processing occurs locally.

The system shall not require:

- Internet connectivity
- Cloud APIs
- External AI services

---

### Modular Design

Each subsystem shall have a single responsibility.

Subsystems must communicate through:

```text
Event Bus
FSM
State Manager
```

---

### Event Driven

All major actions shall be initiated through events.

Example:

```text
FACE_RECOGNIZED
↓
GREETING_QUEUE_CREATED
↓
GREETING_STARTED
↓
GREETING_FINISHED
```

---

### Deterministic Behavior

The system shall produce predictable outputs.

No conversational AI exists in V3.

No runtime language inference exists in V3.

---

# 3. High Level Architecture

```text
Camera
↓
Face Detection
↓
Face Tracking
↓
Face Recognition
↓
Priority Manager
↓
Greeting Manager
↓
Playback Service
↓
Monitoring
```

---

# 4. System Components

The system is composed of the following components:

```text
Camera Service

Face Recognition Service

Face Presence Manager

Priority Manager

Greeting Manager

Playback Service

Finite State Machine

State Manager

Event Bus

Dashboard

Enrollment Module
```

---

# 5. Component Responsibilities

---

# Camera Service

File:

```text
utils/camera_service.py
```

Purpose:

```text
Capture live frames
from the camera.
```

Responsibilities:

- Initialize camera
- Read camera frames
- Publish frame events
- Handle camera failures

Outputs:

```text
Video Frames
```

Does NOT perform:

- Recognition
- Tracking
- Audio playback

---

# Face Recognition Service

File:

```text
utils/face_recognition.py
```

Purpose:

```text
Detect and recognize users.
```

Technology:

```text
MediaPipe Face Detection

+
ArcFace Recognition
```

Responsibilities:

- Face detection
- Face embedding generation
- Face matching
- Multi-user recognition

Outputs:

```text
FACE_RECOGNIZED
FACE_UNKNOWN
```

Events.

---

# Face Presence Manager

File:

```text
utils/face_presence_manager.py
```

Purpose:

```text
Track user presence.
```

Responsibilities:

- Active users
- Presence sessions
- Last seen timestamps
- Face loss tracking

Configuration:

```json
{
  "face_lost_timeout": 5
}
```

Outputs:

```text
FACE_LOST

ALL_USERS_LOST
```

---

# Priority Manager

File:

```text
utils/priority_manager.py
```

Purpose:

```text
Sort recognized users.
```

Input:

```text
Recognized Users
```

Rule:

```text
Lower Number
=
Higher Priority
```

Example:

```text
Priority 1
↓
Priority 2
↓
Priority 3
```

Output:

```text
Sorted Greeting Queue
```

---

# Greeting Manager

File:

```text
utils/greeting_manager.py
```

Purpose:

```text
Build playback sequence.
```

Responsibilities:

- Greeting queue generation
- Greeting ordering
- Interaction mode handling
- Greeting persistence

Inputs:

```text
Sorted Users

Interaction Mode
```

Outputs:

```text
Playback Queue
```

---

# Playback Service

File:

```text
utils/playback.py
```

Purpose:

```text
Play audio files.
```

Responsibilities:

- Audio playback
- Playback queue
- Pause
- Resume
- Playback completion events

Outputs:

```text
PLAYBACK_STARTED

PLAYBACK_FINISHED

PLAYBACK_PAUSED

PLAYBACK_RESUMED
```

---

# Event Bus

File:

```text
utils/event_bus.py
```

Purpose:

```text
Event distribution.
```

Responsibilities:

- Publish events
- Subscribe handlers
- Decouple components

Example:

```text
FACE_RECOGNIZED
↓
Priority Manager
↓
Greeting Manager
```

---

# State Manager

File:

```text
utils/state_manager.py
```

Purpose:

```text
Maintain current system state.
```

Responsibilities:

- Store active state
- Publish state changes
- Provide state lookup

---

# Finite State Machine

File:

```text
utils/fsm.py
```

Purpose:

```text
Control system workflow.
```

Responsibilities:

- State validation
- State transitions
- Transition safety

Reference:

```text
STATE_MACHINE_V3.md
```

---

# Enrollment Module

File:

```text
utils/face_enrollment.py
```

Purpose:

```text
Register new users.
```

Responsibilities:

- Capture enrollment images
- Generate embeddings
- Store user profile

Required enrollment images:

```text
Front Face
Left Face
Right Face
```

---

# Dashboard

Files:

```text
pages/

1_Dashboard.py
2_Enroll_Face.py
3_Settings.py
```

Purpose:

```text
Administration
Monitoring
Configuration
```

---

# 6. Data Flow Architecture

## Single User

```text
Camera
↓
Face Detection
↓
Face Recognition
↓
Priority Manager
↓
Greeting Manager
↓
Playback
↓
Monitoring
```

---

## Multiple Users

```text
Camera
↓
Face Detection
↓
Face Recognition

Manager
Natnael
Visitor

↓

Priority Manager

↓

Manager
Natnael
Visitor

↓

Greeting Manager

↓

Playback Queue

↓

Audio Playback

↓

Monitoring
```

---

# 7. User Data Architecture

Each user contains:

```json
{
  "user_id": "",
  "priority": 0,
  "preferred_language": "",
  "embeddings": [],
  "greeting_audio": "",
  "dialog_audio": ""
}
```

Stored in:

```text
faces/users.json
```

---

# 8. Audio Architecture

Directory:

```text
audio/

english/
amharic/
arabic/
```

Each language contains:

```text
greetings/
dialogs/
```

---

## Greeting Audio

Examples:

```text
manager.wav

natnael.wav

visitor.wav
```

---

## Dialog Audio

Common Dialog:

```text
common_dialog.wav
```

User Dialog:

```text
manager.wav

natnael.wav

visitor.wav
```

---

# 9. Interaction Mode Architecture

Configuration:

```json
{
  "interaction_mode": "common_dialog"
}
```

---

## Mode A

```text
All Greetings
↓
Common Dialog
```

Flow:

```text
PLAY_GREETINGS
↓
PLAY_COMMON_DIALOG
↓
MONITORING
```

---

## Mode B

```text
Greeting
↓
Dialog

Greeting
↓
Dialog
```

Flow:

```text
PLAY_GREETINGS
↓
PLAY_USER_DIALOGS
↓
MONITORING
```

---

# 10. Dialog Interruption Architecture

Purpose:

```text
Future extensibility.
```

Applicable:

```text
Dialog Playback Only
```

Not Applicable:

```text
Greeting Playback
```

Supported Operations:

```text
Pause

Resume

Continue Playback
```

Workflow:

```text
PLAY_DIALOG
↓
INTERRUPT
↓
PAUSED_DIALOG
↓
RESUME
↓
PLAY_DIALOG
```

---

# 11. Monitoring Architecture

After all playback:

```text
MONITORING
```

Responsibilities:

- Track active users
- Detect departures
- Detect arrivals

Must NOT:

- Replay greetings
- Restart dialogs

---

# 12. Face Presence Architecture

Configuration:

```json
{
  "face_lost_timeout": 5
}
```

Workflow:

```text
Face Missing
↓
Timer
↓
FACE_LOST
```

If face returns:

```text
Timer Cancelled
```

---

# 13. System Configuration Files

```text
config/

settings.json

interaction_modes.json
```

Purpose:

- System settings
- Interaction mode
- Timeouts

---

# 14. File Responsibility Matrix

```text
camera_service.py
    Camera Handling

face_recognition.py
    Detection + Recognition

face_presence_manager.py
    Presence Tracking

priority_manager.py
    Priority Ordering

greeting_manager.py
    Queue Creation

playback.py
    Audio Playback

fsm.py
    State Control

state_manager.py
    State Storage

event_bus.py
    Messaging

logger.py
    Logging

face_enrollment.py
    Enrollment
```

---

# 15. Components Removed From V2

The following systems DO NOT exist in V3:

```text
Whisper

Speech-To-Text

Wake Words

Language Detection

Conversation Manager

Scenario Engine

VAD

RNNoise
```

Implementation SHALL NOT reintroduce them.

---

# 16. Deployment Architecture

```text
Raspberry Pi 4
│
├── Camera
│
├── Speaker
│
├── Face Recognition Engine
│
├── Dashboard
│
└── Audio Playback
```

All processing is local.

No cloud components exist.

---

# 17. Success Criteria

Architecture is considered successful when:

✅ Face detection works.

✅ Face recognition works.

✅ Multi-user recognition works.

✅ Priority ordering works.

✅ Greeting queue works.

✅ Dialog playback works.

✅ Interaction modes work.

✅ Interruption framework works.

✅ Monitoring works.

✅ Presence tracking works.

✅ Dashboard configuration works.

✅ Runs fully offline.

---

# End of Document
