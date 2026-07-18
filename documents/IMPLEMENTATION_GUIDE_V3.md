# IMPLEMENTATION_GUIDE_V3.md

# EthioChatbot V3
## Official Implementation Guide for Claude Code

---

# Document Purpose

This document provides the official implementation instructions for EthioChatbot V3.

Its purpose is to ensure:

- Consistent implementation
- Minimal architectural drift
- Reuse of existing components
- Faster development
- Easier maintenance
- Successful end-to-end implementation

This document is the primary implementation guide for Claude Code.

---

# 1. Project Mission

EthioChatbot V3 is a:

```text
Face Recognition
+
Priority Based Greeting
+
Multilingual Audio Information System
```

EthioChatbot V3 is NOT a conversational AI assistant.

The system must remain:

```text
Offline
Deterministic
Lightweight
Raspberry Pi Friendly
Easy to Maintain
```

---

# 2. Documents To Read First

Before modifying any code, read the documents in the following order:

```text
1. PROJECT_SPECIFICATION_V3.md

2. STATE_MACHINE_V3.md

3. SYSTEM_ARCHITECTURE_V3.md

4. AUDIO_STRUCTURE_V3.md

5. ACCEPTANCE_TESTS_V3.md

6. DEVELOPMENT_RULES_V3.md
```

Implementation must follow these documents.

---

# 3. Documentation Priority Order

If two documents appear to conflict:

Priority order is:

```text
PROJECT_SPECIFICATION_V3.md
↓
STATE_MACHINE_V3.md
↓
SYSTEM_ARCHITECTURE_V3.md
↓
AUDIO_STRUCTURE_V3.md
↓
ACCEPTANCE_TESTS_V3.md
↓
DEVELOPMENT_RULES_V3.md
```

Always follow the higher-priority document.

---

# 4. Core Development Objective

Build a complete, demonstratable EthioChatbot V3 capable of:

```text
Multi-User Face Recognition

Priority-Based Greeting

Multilingual Audio Playback

Face Presence Monitoring

Interaction Mode Switching

Dialog Interruption Framework
```

without introducing any speech-processing features.

---

# 5. Features That Must Be Implemented

Claude Code SHALL implement:

✅ Face Detection

✅ Face Recognition

✅ Multi-User Recognition

✅ Face Enrollment

✅ Priority-Based Greeting

✅ Greeting Persistence

✅ Face Presence Tracking

✅ Face Lost Detection

✅ Mode A

✅ Mode B

✅ Common Dialog Playback

✅ User-Specific Dialog Playback

✅ Playback Queue

✅ Dashboard

✅ Settings Management

✅ Dialog Interruption Framework

✅ Monitoring Mode

✅ Return To Face Detection Mode

---

# 6. Features That Must NOT Be Implemented

The following features are explicitly excluded from EthioChatbot V3:

❌ Whisper

❌ Speech-To-Text

❌ Wake Words

❌ Voice Commands

❌ VAD

❌ RNNoise

❌ Language Detection

❌ Conversational AI

❌ Scenario Engine

❌ Chat Logic

❌ Question Answering

❌ LLM Integration

❌ Online AI Services

❌ Cloud Processing

Do not create placeholder implementations for these features.

Do not leave dormant code paths for these features.

---

# 7. Existing Code Reuse Policy

The objective is NOT to rewrite the entire project.

Reuse existing components whenever possible.

---

## Reuse These Modules

```text
camera_service.py

event_bus.py

face_enrollment.py

face_recognition.py

fsm.py

logger.py

playback.py

state_manager.py
```

Only modify them if absolutely necessary.

---

## Implement These Modules

Claude Code should focus development effort on:

```text
greeting_manager.py

priority_manager.py

face_presence_manager.py
```

These modules form the core of V3.

---

# 8. Face Recognition Requirements

---

## Detection Technology

Implement using:

```text
MediaPipe Face Detection
```

Requirements:

```text
Fast

Lightweight

Multi-Face Support

Front Face Support

Side Face Support
```

---

## Recognition Technology

Implement using:

```text
ArcFace

(InsightFace)
```

Requirements:

```text
High Accuracy

Multi-Angle Recognition

Stable Embeddings
```

---

## Enrollment Requirement

Each user shall support:

```text
Front Face

Left Face

Right Face
```

During enrollment.

The system must not assume:

```text
One Image Per User
```

---

# 9. Face Presence Management

Implement:

```text
Active User Tracking

Last Seen Timestamps

Face Lost Detection
```

Configuration:

```json
{
    "face_lost_timeout": 5
}
```

Rules:

```text
Temporary disappearance
≠ Face Lost

Permanent disappearance
= Face Lost
```

---

# 10. Greeting Workflow

When users are recognized:

```text
Recognize Users
↓
Sort By Priority
↓
Create Greeting Queue
↓
Play Greetings
```

Requirements:

```text
Sequential Playback

No Overlap

One Greeting At A Time
```

---

# 11. Priority Rules

Lower priority number means higher importance.

Example:

```text
Manager    1

Natnael    2

Visitor    3
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

# 12. Greeting Persistence

Users must only be greeted once per presence session.

Example:

```text
User Appears
↓
Greeting Played
↓
User Remains Visible
```

No replay is allowed.

---

# 13. Interaction Mode Implementation

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
Greeting User 1
↓
Greeting User 2
↓
Greeting User 3
↓
Play One Common Dialog
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
Greeting User
↓
User Dialog

↓

Greeting User
↓
User Dialog
```

---

# 14. Audio Resolution Rules

Audio path resolution must follow:

```text
preferred_language
```

from the enrolled user.

Example:

```json
{
    "user_id": "natnael",
    "preferred_language": "amharic"
}
```

Greeting file:

```text
audio/amharic/greetings/natnael.wav
```

Mode A dialog:

```text
audio/amharic/dialogs/common_dialog.wav
```

Mode B dialog:

```text
audio/amharic/dialogs/natnael.wav
```

---

# 15. Dialog Interruption Framework

Implement interruption support.

Applies only to:

```text
Dialog Audio
```

Not to:

```text
Greeting Audio
```

Required operations:

```text
Pause

Resume

Continue From Previous Position
```

The framework must preserve:

```text
Playback Position
```

---

# 16. Dashboard Requirements

Dashboard must display:

```text
Current State

Detected Users

Active Users

Greeting Queue

Playback Status

Current Interaction Mode
```

---

# 17. Settings Requirements

Settings page must allow configuration of:

```text
Face Lost Timeout

Interaction Mode

System Settings
```

Settings must persist across restarts.

---

# 18. FSM Implementation Rules

State transitions must conform exactly to:

```text
STATE_MACHINE_V3.md
```

Do not create undocumented states.

Do not skip required transitions.

All transitions must be logged.

---

# 19. Event Bus Usage

Component communication must use:

```text
event_bus.py
```

Avoid direct cross-component calls whenever possible.

Prefer:

```text
Event Publish
↓
Event Subscribe
↓
Action
```

---

# 20. Error Handling

Claude Code must implement graceful handling for:

```text
Missing Audio Files

Missing User Records

Missing Embeddings

Playback Failures

Camera Failures
```

System must:

```text
Log Errors

Continue Operating
```

System crashes are not acceptable.

---

# 21. Logging Requirements

Log:

```text
State Changes

Recognition Events

Greeting Events

Playback Events

Face Loss Events

Errors
```

Avoid excessive debug output.

---

# 22. Performance Goals

Target platform:

```text
Raspberry Pi 4
```

Optimization priorities:

```text
Recognition Accuracy
↓
Recognition Stability
↓
Playback Reliability
↓
UI Responsiveness
↓
Frame Rate
```

Do not sacrifice recognition quality for unnecessary speed.

---

# 23. Validation Requirements

After implementation, validate against:

```text
ACCEPTANCE_TESTS_V3.md
```

All critical tests must pass.

---

# 24. Required Final Deliverables

After implementation, generate:

## Files Modified Report

List:

```text
Modified Files

Created Files

Removed Files
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

Summarize:

```text
Implemented Features

System Status

Deployment Readiness
```

---

# 25. Final Implementation Rule

When faced with multiple implementation options:

Prefer:

```text
Simplicity
↓
Maintainability
↓
Offline Operation
↓
Raspberry Pi Compatibility
↓
Code Reuse
```

Avoid:

```text
Overengineering

Unused Abstractions

Unnecessary Libraries

Unspecified Features
```

If a feature is not defined in the V3 documents:

```text
Do Not Implement It
```

---

# End of Document
