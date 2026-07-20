# CLAUDE.md

# EthioChatbot V3
## Claude Code Implementation Contract

---

# Purpose

This document defines the mandatory rules and implementation constraints for Claude Code.

Before making any code changes, Claude Code must read and follow this file.

This file serves as the implementation contract for EthioChatbot V3.

---

# Project Identity

Project Name:

```text
EthioChatbot V3
```

Project Type:

```text
Offline Robotic Face Recognition Greeting System
```

Primary Goal:

```text
Recognize People
↓
Track People
↓
Sort By Priority
↓
Greet + Nod
↓
Play Dialog Audio
↓
Monitor Presence
```

The system is NOT a conversational chatbot.

---

# Mandatory Documents

Read all documents inside:

```text
documents/
```

Required reading order:

```text
1. PROJECT_SPECIFICATION_V3.md

2. HEAD_MOTION_SPECIFICATION_V3.md

3. STATE_MACHINE_V3.md

4. SYSTEM_ARCHITECTURE_V3.md

5. AUDIO_STRUCTURE_V3.md

6. DEVELOPMENT_RULES_V3.md

7. IMPLEMENTATION_GUIDE_V3.md

8. ACCEPTANCE_TESTS_V3.md
```

These documents are the source of truth.

---

# Documentation Priority

If documents appear to conflict:

Priority:

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

Higher priority documents always win.

---

# EthioChatbot V3 Scope

EthioChatbot V3 is a:

```text
Face Recognition
+
Robotic Head Tracking
+
Priority Greeting
+
Multilingual Audio Playback
System
```

The project must remain:

```text
Offline

Deterministic

Lightweight

Reliable

Maintainable

Raspberry Pi Friendly
```

---

# Features To Implement

Claude Code SHALL implement:

✅ Face Detection

✅ Face Recognition

✅ Face Enrollment

✅ Multi-Angle Enrollment

✅ Multi-User Recognition

✅ Face Presence Tracking

✅ Face Loss Detection

✅ Priority Management

✅ Greeting Queue

✅ Greeting Persistence

✅ Mode A

✅ Mode B

✅ Playback Queue

✅ Dialog Playback

✅ Dialog Interruption

✅ Restart Greetings

✅ Dashboard

✅ Settings

✅ Monitoring Mode

✅ Yaw Surveillance

✅ Face Tracking

✅ Greeting Nodding

✅ Servo Centering

✅ Fully Offline Operation

---

# Features Explicitly Forbidden

The following features SHALL NOT exist in EthioChatbot V3.

Do not implement:

```text
Whisper

Speech-To-Text

STT

Wake Words

Voice Commands

Voice Recognition

Language Detection

RNNoise

Voice Activity Detection

Scenario Engine

Conversation Manager

Question Answering

Conversational AI

Chat Logic

OpenAI APIs

LLMs

Cloud AI Services

Internet-Based Processing
```

These belong to V2 and are permanently removed.

---

# Hardware Target

EthioChatbot V3 targets:

```text
Raspberry Pi 4

8GB RAM
32GB Storage
1.8GHz CPU
```

Optimization priority:

```text
Recognition Accuracy
↓
Recognition Stability
↓
Servo Reliability
↓
Playback Reliability
↓
Dashboard Responsiveness
↓
Frame Rate
```

---

# Approved Technologies

Face Detection:

```text
MediaPipe Face Detection
```

Face Recognition:

```text
InsightFace
ArcFace Embeddings
```

Face Tracking:

```text
Centroid Tracking
```

Dashboard:

```text
Streamlit
```

Configuration:

```text
JSON
```

Event Architecture:

```text
FSM

Event Bus

State Manager
```

---

# Existing Project Structure

Do not reorganize the repository unless necessary.

Current structure is intentional.

```text
app.py

audio/
config/
documents/
faces/
logs/
models/
pages/
utils/
```

Preserve this structure.

---

# Existing Modules To Reuse

Do not rewrite without justification.

```text
camera_service.py

event_bus.py

face_enrollment.py

face_recognition.py

fsm.py

state_manager.py

playback.py

logger.py
```

These are considered core project assets.

---

# New Core Module

The following module is considered a primary implementation target:

```text
head_motion_controller.py
```

Responsibilities:

```text
Yaw Scanning

Yaw Tracking

Pitch Nodding

Head Centering
```

---

# Robotic Neck Specification

The robot contains:

```text
Yaw Servo
Pitch Servo
```

No additional body motion exists.

---

## Yaw Servo

Purpose:

```text
Left / Right Rotation
```

Responsibilities:

```text
Surveillance

Face Tracking

User Following
```

---

## Pitch Servo

Purpose:

```text
Up / Down Rotation
```

Responsibilities:

```text
Greeting Nodding
```

Pitch shall NOT:

```text
Track Users

Run Surveillance Patterns
```

---

# Surveillance Behavior

FSM State:

```text
FACE_DETECTION_MODE
```

Action:

```text
Yaw Scan Active
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

# Face Tracking Behavior

FSM States:

```text
FACE_DETECTED

FACE_RECOGNIZED

MONITORING
```

Action:

```text
Yaw Tracks User
```

Preferred target:

```text
Highest Priority Visible User
```

---

# Greeting Nodding Behavior

FSM State:

```text
PLAY_GREETINGS
```

Each greeting must trigger:

```text
Greeting Audio
+
Pitch Nod
```

Nodding pattern:

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

# Dialog Behavior

When dialogs are playing:

```text
Yaw Tracking Active

Pitch Neutral
```

Dialogs must never trigger nodding.

---

# User Enrollment Rules

Each user shall support:

```text
Front Face

Left Face

Right Face
```

Do not assume:

```text
Single Image Enrollment
```

is sufficient.

---

# Supported Languages

Only:

```text
English

Amharic

Arabic
```

Language selection comes from:

```text
preferred_language
```

stored in the user profile.

No runtime language detection exists.

---

# Priority Rules

Lower number means higher priority.

Example:

```text
Manager   1

Natnael   2

Visitor   3
```

Greeting order:

```text
Manager
↓
Natnael
↓
Visitor
```

This behavior is mandatory.

---

# Multi-User Rules

Recognition must complete before greeting begins.

Example:

```text
Recognize Users
↓
Priority Sort
↓
Build Greeting Queue
↓
Execute Greetings
```

Do not begin greeting while discovery is ongoing.

---

# Greeting Persistence Rules

A user may only be greeted once per presence session.

Allowed:

```text
Appear
↓
Greeting
↓
Remain Visible
```

Result:

```text
No Replay
```

---

# Face Persistence Rules

Configuration:

```json
{
  "face_lost_timeout": 5
}
```

Temporary disappearance:

```text
User Returns Before Timeout
```

Result:

```text
No FACE_LOST

No Re-Greeting
```

---

# Interaction Modes

Only two modes are supported.

---

## Mode A

Configuration:

```json
{
  "interaction_mode": "common_dialog"
}
```

Behavior:

```text
Greeting + Nod
↓
Greeting + Nod
↓
Greeting + Nod
↓
Common Dialog
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

---

## Mode B

Configuration:

```json
{
  "interaction_mode": "user_specific_dialog"
}
```

Behavior:

```text
Greeting + Nod + Dialog
↓
Greeting + Nod + Dialog
↓
Greeting + Nod + Dialog
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

---

# Dialog Interruption Rules

Applies only to:

```text
Dialogs
```

Never:

```text
Greetings
```

Supported operations:

```text
Pause

Resume

Continue Playback
```

Resume must:

```text
Continue From Previous Position
```

not restart.

---

# Restart Greetings Rules

Dashboard shall provide:

```text
Restart Greetings
```

Behavior:

```text
Stop Dialog Playback
↓
Clear Greeting Session
↓
Rebuild Queue
↓
Replay Greetings
↓
Replay Dialogs
```

Application must not restart.

---

# Dashboard Rules

Dashboard pages shall remain UI-only.

Dashboard responsibilities:

```text
Display System State

Display Users

Display Greeting Queue

Display Servo Status

Display Playback Status
```

Controls:

```text
Pause Dialog

Resume Dialog

Restart Greetings

Center Head

Switch Mode
```

---

# FSM Rules

Follow:

```text
STATE_MACHINE_V3.md
```

exactly.

Do not:

```text
Create Extra States

Skip States

Merge States
```

State transitions must be logged.

---

# Event Bus Rules

Use:

```text
event_bus.py
```

for component communication.

Preferred:

```text
Publish Event
↓
Subscribe Event
↓
Action
```

Avoid direct service coupling.

---

# Audio Rules

Follow:

```text
AUDIO_STRUCTURE_V3.md
```

exactly.

Greeting audio:

```text
audio/<language>/greetings/
```

Dialog audio:

```text
audio/<language>/dialogs/
```

Do not hardcode paths.

---

# Error Handling Rules

The system must continue operating after:

```text
Missing Audio

Missing User Data

Missing Embeddings

Servo Failure

Camera Failure

Playback Failure
```

Log errors.

Avoid crashes.

---

# Logging Rules

Log:

```text
State Changes

Recognition Events

Servo Events

Tracking Events

Greeting Events

Playback Events

Errors
```

Avoid excessive debug noise.

---

# Validation Requirements

Before implementation is considered complete:

Validate against:

```text
ACCEPTANCE_TESTS_V3.md
```

All critical tests must pass.

---

# Required Deliverables

Upon completion generate:

### Files Created Report

```text
Created Files
```

### Files Modified Report

```text
Modified Files
```

### Validation Report

```text
Passed Tests

Failed Tests

Known Issues
```

### Demo Readiness Report

```text
Feature Summary

Deployment Status

Known Limitations
```

---

# Final Instruction

If a feature is not described inside:

```text
PROJECT_SPECIFICATION_V3.md
```

or

```text
HEAD_MOTION_SPECIFICATION_V3.md
```

then:

```text
DO NOT IMPLEMENT IT.
```

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

Architectural Complexity

Unspecified Functionality
```

---

# End of File
