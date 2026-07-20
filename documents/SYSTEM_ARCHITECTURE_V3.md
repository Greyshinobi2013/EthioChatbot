# SYSTEM_ARCHITECTURE_V3.md

# EthioChatbot V3
## System Architecture Specification

---

# Document Purpose

This document defines the complete architecture of EthioChatbot V3.

The purpose of this architecture is to provide:

- Face detection
- Face recognition
- Multi-user recognition
- Priority-based greetings
- Multilingual audio playback
- Robotic head tracking
- Greeting nodding
- Presence monitoring
- Dashboard management

while remaining:

```text
Offline
Deterministic
Modular
Maintainable
Raspberry Pi Friendly
```

---

# 1. System Overview

EthioChatbot V3 is an offline robotic greeting system.

The robot:

```text
Searches For People
↓
Detects Faces
↓
Recognizes Users
↓
Tracks Visible Users
↓
Sorts Users By Priority
↓
Greets Users
↓
Performs Greeting Nods
↓
Plays Dialog Audio
↓
Monitors Presence
```

---

# 2. High-Level Architecture

```text
Camera
↓
Face Detection
↓
Face Recognition
↓
Face Presence Manager
↓
Priority Manager
↓
Greeting Manager
↓
Playback Service
↓
Monitoring
```

Robotic Head Motion operates alongside:

```text
Camera
↓
Face Detection
↓
Head Motion Controller
        │
        ├── Yaw Tracking
        └── Pitch Nodding
```

---

# 3. Hardware Architecture

## Computing Platform

```text
Raspberry Pi 4

8GB RAM
32GB Storage
1.8 GHz CPU
```

---

## Peripherals

```text
Camera

Speaker

Display (Optional)

Yaw Servo

Pitch Servo
```

---

## Neck Assembly

The robotic neck consists of:

```text
Yaw Servo
+
Pitch Servo
```

### Yaw Servo

Purpose:

```text
Horizontal Neck Rotation
```

Responsibilities:

```text
Surveillance Scanning

Face Tracking

User Following
```

---

### Pitch Servo

Purpose:

```text
Vertical Neck Rotation
```

Responsibilities:

```text
Greeting Nodding

Acknowledgement Motion
```

---

# 4. Software Architecture

EthioChatbot V3 is composed of:

```text
Camera Service

Face Recognition Service

Face Presence Manager

Priority Manager

Greeting Manager

Head Motion Controller

Playback Service

FSM

State Manager

Event Bus

Dashboard

Enrollment Module
```

---

# 5. Component Architecture

---

# Camera Service

File:

```text
utils/camera_service.py
```

Purpose:

```text
Provide live video frames.
```

Responsibilities:

```text
Initialize camera

Read frames

Publish frames

Handle camera failures
```

Outputs:

```text
Video Frames
```

Consumes:

```text
Camera Device
```

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

Technologies:

```text
MediaPipe Face Detection

ArcFace Recognition
```

Responsibilities:

```text
Face Detection

Face Encoding

Face Matching

Multi-User Recognition
```

Outputs:

```text
FACE_DETECTED

FACE_RECOGNIZED
```

Events.

---

# Face Enrollment Module

File:

```text
utils/face_enrollment.py
```

Purpose:

```text
Register users.
```

Responsibilities:

```text
Capture Images

Generate Embeddings

Store User Profiles
```

Required Enrollment Images:

```text
Front Face

Left Face

Right Face
```

---

# Face Presence Manager

File:

```text
utils/face_presence_manager.py
```

Purpose:

```text
Track active users.
```

Responsibilities:

```text
Last Seen Timestamps

Active Users

Face Persistence

Face Loss Tracking
```

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

Rule:

```text
Lower Number
=
Higher Priority
```

Example:

```text
Manager     1

Natnael     2

Visitor     3
```

Result:

```text
Manager
↓
Natnael
↓
Visitor
```

Outputs:

```text
Priority Sorted User List
```

---

# Greeting Manager

File:

```text
utils/greeting_manager.py
```

Purpose:

```text
Generate playback sequences.
```

Responsibilities:

```text
Greeting Queue

Mode A Logic

Mode B Logic

Greeting Persistence
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
Play audio content.
```

Responsibilities:

```text
Play

Pause

Resume

Stop

Queue Execution
```

Supported Features:

```text
Mode A

Mode B

Dialog Interruption
```

Outputs:

```text
PLAYBACK_STARTED

PLAYBACK_FINISHED

PLAYBACK_PAUSED

PLAYBACK_RESUMED
```

---

# Head Motion Controller

File:

```text
utils/head_motion_controller.py
```

Purpose:

```text
Control robotic neck movement.
```

Responsibilities:

```text
Yaw Scanning

Yaw Tracking

Pitch Nodding

Servo Centering
```

---

## Public Methods

```python
start_scan()

stop_scan()

track_face(face_position)

greet_nod()

center_head()
```

---

# Head Motion Responsibilities

## Surveillance

State:

```text
FACE_DETECTION_MODE
```

Action:

```text
Yaw Scan
```

Pattern:

```text
Left
↓
Center
↓
Right
↓
Center
```

Repeat.

---

## Face Tracking

States:

```text
FACE_DETECTED

FACE_RECOGNIZED

MONITORING
```

Action:

```text
Track highest-priority visible user.
```

---

## Greeting Nodding

State:

```text
PLAY_GREETINGS
```

Action:

```text
Greeting Audio
+
Pitch Nodding
```

Pattern:

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

---

# Event Bus

File:

```text
utils/event_bus.py
```

Purpose:

```text
Component communication.
```

Responsibilities:

```text
Event Publishing

Event Subscription

Event Distribution
```

---

# State Manager

File:

```text
utils/state_manager.py
```

Purpose:

```text
Store current system state.
```

Responsibilities:

```text
Current State

State Lookup

State Metadata
```

---

# FSM

File:

```text
utils/fsm.py
```

Purpose:

```text
Control workflow.
```

Reference:

```text
STATE_MACHINE_V3.md
```

Responsibilities:

```text
State Validation

Transitions

State Actions
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
Monitoring

Administration

Configuration
```

---

# Dashboard Responsibilities

Display:

```text
Current State

Detected Users

Active Users

Greeting Queue

Playback Status

Current Mode

Servo Status

Yaw Position

Pitch Position
```

Controls:

```text
Pause Dialog

Resume Dialog

Restart Greetings

Center Head

Switch Interaction Mode
```

---

# 6. Data Architecture

---

# User Data

Location:

```text
faces/users.json
```

Structure:

```json
{
  "user_id": "",
  "priority": 0,
  "preferred_language": ""
}
```

---

# Face Images

Location:

```text
faces/images/
```

Contains:

```text
Front Face

Left Face

Right Face
```

Images.

---

# Face Embeddings

Location:

```text
faces/embeddings/
```

Contains:

```text
ArcFace Embeddings
```

for every enrolled user.

---

# 7. Audio Architecture

Reference:

```text
AUDIO_STRUCTURE_V3.md
```

---

## Language Folders

```text
audio/

english/

amharic/

arabic/

common/
```

---

## Greeting Audio

Location:

```text
audio/<language>/greetings/
```

---

## Dialog Audio

Location:

```text
audio/<language>/dialogs/
```

---

# 8. Interaction Modes

---

# Mode A

Configuration:

```json
{
  "interaction_mode": "common_dialog"
}
```

Workflow:

```text
Greeting + Nod
↓
Greeting + Nod
↓
Greeting + Nod
↓
Common Dialog
```

System State Flow:

```text
PLAY_GREETINGS
↓
PLAY_COMMON_DIALOG
↓
MONITORING
```

---

# Mode B

Configuration:

```json
{
  "interaction_mode": "user_specific_dialog"
}
```

Workflow:

```text
Greeting + Nod + Dialog
↓
Greeting + Nod + Dialog
↓
Greeting + Nod + Dialog
```

System State Flow:

```text
PLAY_GREETINGS
↓
PLAY_USER_DIALOGS
↓
MONITORING
```

---

# 9. Dialog Interruption Architecture

Purpose:

```text
Future Interactivity
```

Supports:

```text
Pause

Resume

Continue Playback
```

Applies To:

```text
Dialogs Only
```

Does Not Apply To:

```text
Greetings
```

---

## Dialog Pause

```text
Dialog Playing
↓
Pause
↓
Store Playback Position
```

---

## Dialog Resume

```text
Resume
↓
Continue From Saved Position
```

The dialog must not restart from the beginning.

---

# 10. Monitoring Architecture

State:

```text
MONITORING
```

Responsibilities:

```text
Face Tracking

Presence Tracking

User Monitoring
```

---

## Head Behavior

Yaw:

```text
Track Active User
```

Pitch:

```text
Neutral
```

---

# 11. Face Presence Architecture

Temporary Loss:

```text
Face Missing
↓
Returns Within Timeout
```

Result:

```text
No FACE_LOST
```

---

Permanent Loss:

```text
Face Missing
↓
5 Seconds Pass
```

Result:

```text
FACE_LOST
```

---

All Users Lost:

```text
ALL_USERS_LOST
↓
FACE_DETECTION_MODE
```

---

# 12. Components Removed From V2

The following systems shall NOT exist:

```text
Whisper

Speech-To-Text

Wake Words

Language Detection

Scenario Engine

Conversation Manager

RNNoise

VAD
```

These features are outside the scope of EthioChatbot V3.

---

# 13. Design Principles

The architecture shall prioritize:

```text
Recognition Accuracy
↓
Recognition Stability
↓
Playback Reliability
↓
Servo Reliability
↓
Maintainability
```

over unnecessary complexity.

---

# 14. Success Criteria

Architecture is considered successful when:

✅ Face Detection Works

✅ Face Recognition Works

✅ Multi-User Recognition Works

✅ Face Tracking Works

✅ Yaw Scanning Works

✅ Greeting Nodding Works

✅ Priority Sorting Works

✅ Greeting Queue Works

✅ Mode A Works

✅ Mode B Works

✅ Dialog Interruption Works

✅ Monitoring Works

✅ Dashboard Controls Work

✅ Runs Fully Offline

✅ Runs On Raspberry Pi 4

---

# End of Document
