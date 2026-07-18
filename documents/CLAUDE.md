# CLAUDE.md

# EthioChatbot V3
## Claude Code Implementation Contract

---

# Purpose

This file provides mandatory implementation instructions for Claude Code.

It acts as a contract between the project owner and Claude Code.

Before writing, modifying, deleting, or refactoring code, Claude Code must read and follow this document.

---

# Project Identity

Project Name:

```text
EthioChatbot V3
```

Project Type:

```text
Offline Face Recognition System
```

Purpose:

```text
Recognize registered users
↓
Sort users by priority
↓
Play greetings
↓
Play informational dialogs
↓
Monitor user presence
```

EthioChatbot V3 is NOT a conversational AI system.

---

# Mandatory Documents

Before implementing any feature, read the following files completely:

```text
documents/

PROJECT_SPECIFICATION_V3.md

STATE_MACHINE_V3.md

SYSTEM_ARCHITECTURE_V3.md

AUDIO_STRUCTURE_V3.md

ACCEPTANCE_TESTS_V3.md

DEVELOPMENT_RULES_V3.md

IMPLEMENTATION_GUIDE_V3.md
```

These files are the source of truth.

---

# Documentation Hierarchy

If documentation appears to conflict:

Priority order:

```text
PROJECT_SPECIFICATION_V3.md
↓
STATE_MACHINE_V3.md
↓
SYSTEM_ARCHITECTURE_V3.md
↓
IMPLEMENTATION_GUIDE_V3.md
↓
AUDIO_STRUCTURE_V3.md
↓
DEVELOPMENT_RULES_V3.md
↓
ACCEPTANCE_TESTS_V3.md
```

Always follow the higher-priority document.

---

# Project Scope

Implement ONLY what is described in the V3 documents.

Do not invent features.

Do not extend requirements.

Do not redesign the system.

---

# Existing Repository Structure

The repository structure is intentional.

Do not reorganize folders unless explicitly required.

Current architecture:

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

Keep the structure intact.

---

# Features To Implement

The following features SHALL be implemented.

```text
Face Detection

Face Recognition

Face Enrollment

Multi-User Recognition

Priority Sorting

Greeting Queue

Greeting Persistence

Face Presence Tracking

Face Lost Detection

Mode A

Mode B

Playback Queue

Dialog Playback

Dialog Interruption

Monitoring Mode

Dashboard

Settings
```

---

# Features Explicitly Forbidden

The following features shall NOT exist in EthioChatbot V3.

Do not implement them.

Do not add placeholders for them.

Do not leave partial code for them.

```text
Whisper

Speech-To-Text (STT)

Wake Words

Voice Commands

Voice Interaction

RNNoise

VAD

Language Detection

Conversational AI

Question Answering

Scenario Engine

Conversation Manager

Large Language Models

Cloud Processing

Remote AI APIs
```

---

# Core Design Philosophy

EthioChatbot V3 must remain:

```text
Offline

Simple

Deterministic

Maintainable

Raspberry Pi Friendly
```

When choosing between two solutions:

Prefer:

```text
Simpler Solution
```

---

# Existing Modules

These files already exist and should be reused whenever possible.

```text
camera_service.py

face_recognition.py

face_enrollment.py

event_bus.py

state_manager.py

fsm.py

playback.py

logger.py
```

Avoid rewriting them unless absolutely necessary.

---

# New Core Modules

The primary implementation effort should focus on:

```text
greeting_manager.py

priority_manager.py

face_presence_manager.py
```

These modules are central to V3.

---

# Face Recognition Requirements

---

## Face Detection

Use:

```text
MediaPipe Face Detection
```

Requirements:

```text
Real-Time

Multi-Face

Frontal Faces

Side Faces
```

---

## Face Recognition

Use:

```text
ArcFace

(InsightFace)
```

Requirements:

```text
High Accuracy

Stable Recognition

Multi-Angle Support
```

---

## Enrollment

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

---

# User Profiles

Users contain:

```text
User ID

Priority

Preferred Language

Embeddings

Greeting Audio

Dialog Audio
```

Stored in:

```text
faces/users.json
```

---

# Supported Languages

Only:

```text
English

Amharic

Arabic
```

Language comes from:

```text
Enrollment Profile
```

Do not perform runtime language detection.

---

# Priority Rules

Lower number means higher priority.

Example:

```text
Priority 1
↓
Priority 2
↓
Priority 3
```

Correct order:

```text
1
↓
2
↓
3
```

Never reverse this behavior.

---

# Greeting Rules

Users must be greeted sequentially.

Example:

```text
Manager Greeting
↓
Natnael Greeting
↓
Visitor Greeting
```

Audio overlap is prohibited.

---

# Greeting Persistence

A user may only be greeted once during a presence session.

Allowed:

```text
Appear
↓
Greeting
↓
Remain Visible
```

Not Allowed:

```text
Appear
↓
Greeting
↓
Greeting Again
```

without leaving first.

---

# Face Presence Rules

Configuration:

```json
{
    "face_lost_timeout": 5
}
```

Behavior:

```text
Face Missing
↓
Timer
↓
FACE_LOST
```

Temporary disappearance must not trigger:

```text
FACE_LOST

Re-Greeting

Session Reset
```

---

# Interaction Modes

EthioChatbot V3 supports exactly two modes.

No additional modes may be created.

---

## Mode A

```text
All Greetings
↓
Common Dialog
```

Configuration:

```json
{
    "interaction_mode": "common_dialog"
}
```

---

## Mode B

```text
Greeting
↓
User Dialog

↓

Greeting
↓
User Dialog
```

Configuration:

```json
{
    "interaction_mode": "user_specific_dialog"
}
```

---

# Dialog Interruption Framework

Applies only to:

```text
Dialog Playback
```

Not:

```text
Greeting Playback
```

Required operations:

```text
Pause

Resume

Continue Playback
```

Resume must continue from the previous playback position.

Never restart automatically.

---

# FSM Rules

FSM implementation must follow:

```text
STATE_MACHINE_V3.md
```

exactly.

Do not:

```text
Skip States

Merge States

Create Undocumented States
```

State transitions must be logged.

---

# Event Bus Rules

Use:

```text
event_bus.py
```

for component communication.

Prefer:

```text
Publish Event
↓
Subscribe Event
↓
Action
```

Avoid direct coupling between modules.

---

# Dashboard Rules

Dashboard must remain lightweight.

Dashboard responsibilities:

```text
Display Status

Display Users

Display Playback

Change Settings

Switch Modes
```

Dashboard must not contain business logic.

---

# Audio Rules

Follow:

```text
AUDIO_STRUCTURE_V3.md
```

exactly.

Supported folders:

```text
audio/english/

audio/amharic/

audio/arabic/

audio/common/
```

Greeting audio:

```text
greetings/
```

Dialog audio:

```text
dialogs/
```

---

# Error Handling Rules

The system must continue running after:

```text
Missing Audio

Invalid User

Playback Error

Camera Error

Missing Embeddings
```

Log errors.

Avoid crashes.

---

# Logging Rules

Log:

```text
State Changes

Recognition Events

Greeting Events

Playback Events

Face Lost Events

Errors
```

Avoid noisy logging.

---

# Raspberry Pi Rules

Target Hardware:

```text
Raspberry Pi 4

8GB RAM

32GB Storage

1.8GHz CPU
```

Optimization priorities:

```text
Recognition Accuracy
↓
Recognition Stability
↓
Playback Reliability
↓
Responsiveness
```

Avoid unnecessary CPU-intensive designs.

---

# Validation Requirement

Before declaring work complete:

Validate against:

```text
ACCEPTANCE_TESTS_V3.md
```

Every critical test must pass.

---

# Required Final Reports

Upon completion generate:

---

## Files Modified Report

```text
Created Files

Modified Files

Removed Files
```

---

## Validation Report

```text
Passed Tests

Failed Tests

Known Issues
```

---

## Demo Readiness Report

```text
Complete Feature List

System Status

Deployment Readiness
```

---

# Final Instruction

If a feature is not described in:

```text
PROJECT_SPECIFICATION_V3.md
```

then:

```text
DO NOT IMPLEMENT IT.
```

Favor:

```text
Simplicity

Maintainability

Offline Operation

Code Reuse

Raspberry Pi Compatibility
```

over introducing new complexity.

---

# End of File
