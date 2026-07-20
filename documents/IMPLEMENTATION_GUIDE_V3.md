# IMPLEMENTATION_GUIDE_V3.md

# EthioChatbot V3
## Official Implementation Guide

---

# Document Purpose

This document provides the official implementation roadmap and engineering guide for EthioChatbot V3.

The objective is to ensure that all implementations:

- Follow the approved specifications
- Follow the approved architecture
- Preserve project scope
- Maintain Raspberry Pi compatibility
- Remain fully offline
- Produce a complete demonstratable system

This document serves as the primary implementation reference for Claude Code and future developers.

---

# 1. Project Objective

EthioChatbot V3 is a:

```text
Face Recognition
+
Robotic Greeting
+
Multilingual Information System
```

The system shall:

```text
Recognize Users
↓
Track Users
↓
Sort By Priority
↓
Perform Greeting + Nod
↓
Play Dialog Audio
↓
Monitor Presence
```

The system shall remain:

```text
Offline

Deterministic

Lightweight

Maintainable

Extensible
```

---

# 2. Documents To Read Before Coding

Implementation must begin by reading the project documents in the following order:

```text
1. PROJECT_SPECIFICATION_V3.md

2. HEAD_MOTION_SPECIFICATION_V3.md

3. STATE_MACHINE_V3.md

4. SYSTEM_ARCHITECTURE_V3.md

5. AUDIO_STRUCTURE_V3.md

6. DEVELOPMENT_RULES_V3.md

7. ACCEPTANCE_TESTS_V3.md

8. CLAUDE.md
```

All implementation decisions must follow these documents.

---

# 3. Documentation Authority

If multiple documents appear to conflict:

Priority order:

```text
PROJECT_SPECIFICATION_V3.md
↓
HEAD_MOTION_SPECIFICATION_V3.md
↓
STATE_MACHINE_V3.md
↓
SYSTEM_ARCHITECTURE_V3.md
↓
DEVELOPMENT_RULES_V3.md
↓
IMPLEMENTATION_GUIDE_V3.md
↓
ACCEPTANCE_TESTS_V3.md
↓
CLAUDE.md
```

The higher document wins.

---

# 4. Features To Implement

Claude Code shall implement:

✅ Face Detection

✅ Face Recognition

✅ Face Enrollment

✅ Multi-User Recognition

✅ Multi-Angle Enrollment

✅ Face Presence Tracking

✅ Priority Sorting

✅ Greeting Queue

✅ Greeting Persistence

✅ Face Tracking

✅ Yaw Surveillance

✅ Greeting Nodding

✅ Mode A

✅ Mode B

✅ Dialog Playback

✅ Dialog Interruption

✅ Restart Greetings

✅ Monitoring Mode

✅ Dashboard

✅ Settings

✅ Fully Offline Operation

---

# 5. Features Explicitly Excluded

Do NOT implement:

```text
Speech-To-Text

Whisper

Wake Words

Voice Commands

RNNoise

Voice Activity Detection

Language Detection

Conversational AI

Question Answering

Scenario Engines

Conversation Managers

Large Language Models

Cloud Services
```

These technologies are permanently removed from V3.

---

# 6. Recommended Implementation Order

The project shall be built in phases.

---

# Phase 1
## Core Infrastructure

Verify and implement:

```text
event_bus.py

fsm.py

state_manager.py

logger.py
```

Requirements:

```text
State transitions work

Events work

Logging works
```

---

# Phase 2
## Camera System

Implement:

```text
camera_service.py
```

Requirements:

```text
Camera initialization

Frame acquisition

Frame delivery
```

---

# Phase 3
## Face Detection

Implement:

```text
MediaPipe Face Detection
```

Requirements:

```text
Single-face detection

Multi-face detection

Front-face support

Side-face support
```

Verification:

```text
Faces detected correctly
```

---

# Phase 4
## Face Recognition

Implement:

```text
ArcFace Recognition
```

Requirements:

```text
Face embeddings

Face matching

User identification
```

Verification:

```text
Recognized user IDs returned
```

---

# Phase 5
## Face Enrollment

Implement:

```text
face_enrollment.py
```

Requirements:

Capture:

```text
Front Face

Left Face

Right Face
```

Generate:

```text
ArcFace Embeddings
```

Store:

```text
User Profile

Embeddings
```

---

# Phase 6
## Head Motion Controller

Implement:

```text
head_motion_controller.py
```

Responsibilities:

```text
Yaw Scanning

Yaw Tracking

Pitch Nodding

Servo Centering
```

---

## Required Methods

```python
start_scan()

stop_scan()

track_face(face_position)

greet_nod()

center_head()
```

---

# Phase 7
## Face Presence Management

Implement:

```text
face_presence_manager.py
```

Responsibilities:

```text
Track Active Users

Track Last Seen

Face Loss Detection

All Users Lost Detection
```

Configuration:

```json
{
  "face_lost_timeout": 5
}
```

---

# Phase 8
## Priority Manager

Implement:

```text
priority_manager.py
```

Requirements:

```text
Sort Users

Priority Ordering

Tie Handling
```

Sorting rule:

```text
Lower Number
=
Higher Priority
```

---

# Phase 9
## Greeting Manager

Implement:

```text
greeting_manager.py
```

Responsibilities:

```text
Greeting Queue

Greeting Persistence

Mode Handling
```

---

# Greeting Rules

Every greeting shall:

```text
Play Greeting Audio

+
Start Nod Animation
```

The nod occurs with greeting playback.

---

# Phase 10
## Playback Service

Implement:

```text
playback.py
```

Responsibilities:

```text
Play

Pause

Resume

Stop

Queue Execution
```

Playback must remain sequential.

---

# Phase 11
## Mode A

Implement:

```text
Common Dialog Mode
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

After playback:

```text
MONITORING
```

---

# Phase 12
## Mode B

Implement:

```text
User Specific Dialog Mode
```

Workflow:

```text
Greeting + Nod + Dialog
↓
Greeting + Nod + Dialog
↓
Greeting + Nod + Dialog
```

After playback:

```text
MONITORING
```

---

# Phase 13
## Dialog Interruption

Implement:

```text
Pause

Resume

Continue Playback
```

Applies only to:

```text
Dialogs
```

Not to:

```text
Greetings
```

---

## Pause Workflow

```text
Dialog Playing
↓
Pause
↓
Store Position
```

---

## Resume Workflow

```text
Resume
↓
Continue From Stored Position
```

Dialog must not restart.

---

# Phase 14
## Restart Greetings

Implement dashboard command:

```text
Restart Greetings
```

Workflow:

```text
Stop Current Dialog
↓
Clear Greeting Session
↓
Rebuild Greeting Queue
↓
Replay Greetings
↓
Replay Dialogs
```

---

# Phase 15
## Dashboard

Implement:

```text
1_Dashboard.py
```

Display:

```text
Current State

Detected Users

Active Users

Greeting Queue

Playback Status

Mode

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

Interaction Mode
```

---

# Phase 16
## Settings

Implement:

```text
3_Settings.py
```

Manage:

```text
Face Lost Timeout

Interaction Mode

Servo Settings

Application Settings
```

Settings must persist.

---

# Head Motion Implementation

---

## Surveillance State

FSM State:

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

Repeat continuously.

---

## Face Tracking State

FSM States:

```text
FACE_DETECTED

FACE_RECOGNIZED

MONITORING
```

Action:

```text
Track Visible User
```

Priority:

```text
Highest-Priority User
```

---

## Greeting State

FSM State:

```text
PLAY_GREETINGS
```

Action:

```text
Greeting Audio
+
Pitch Nod
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

## Dialog State

FSM States:

```text
PLAY_COMMON_DIALOG

PLAY_USER_DIALOGS
```

Action:

```text
Yaw Tracking ON

Pitch Neutral
```

No nodding.

---

# Data Storage

---

## Users

Location:

```text
faces/users.json
```

---

## Face Images

Location:

```text
faces/images/
```

---

## Embeddings

Location:

```text
faces/embeddings/
```

---

# Audio Resolution Rules

Follow:

```text
AUDIO_STRUCTURE_V3.md
```

Greeting:

```text
audio/<language>/greetings/<user>.wav
```

---

Mode A:

```text
audio/<language>/dialogs/common_dialog.wav
```

---

Mode B:

```text
audio/<language>/dialogs/<user>.wav
```

---

# Validation Requirements

After implementation validate against:

```text
ACCEPTANCE_TESTS_V3.md
```

All critical tests must pass.

---

# Required Reports

Upon completion generate:

---

## Files Created Report

List:

```text
Created Files
```

---

## Files Modified Report

List:

```text
Modified Files
```

---

## Validation Report

Provide:

```text
Passed Tests

Failed Tests

Known Issues
```

---

## Demo Readiness Report

Provide:

```text
Completed Features

Remaining Work

Deployment Status
```

---

# Final Engineering Rule

When multiple implementation choices exist:

Prefer:

```text
Simplicity
↓
Offline Operation
↓
Maintainability
↓
Recognition Accuracy
↓
Raspberry Pi Compatibility
```

Avoid:

```text
Overengineering

Unused Features

Complex Architectures

Unapproved Technologies
```

If a feature is not specified:

```text
Do Not Implement It
```

---

# End of Document
