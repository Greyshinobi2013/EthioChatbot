# DEVELOPMENT_RULES_V3.md

# EthioChatbot V3
## Development Rules, Engineering Constraints and Implementation Standards

---

# Document Purpose

This document defines the mandatory development rules for EthioChatbot V3.

These rules must be followed by:

- Claude Code
- Human Developers
- Future Contributors
- Project Maintainers

The purpose of this document is to:

- Prevent architecture drift
- Prevent scope creep
- Preserve maintainability
- Ensure Raspberry Pi compatibility
- Preserve deterministic behavior
- Guarantee compliance with project specifications

---

# 1. Core Project Philosophy

EthioChatbot V3 is a:

```text
Face Recognition
+
Robotic Greeting
+
Multilingual Audio Information System
```

EthioChatbot V3 is NOT a conversational chatbot.

The primary focus is:

```text
User Recognition
↓
Head Tracking
↓
Priority Sorting
↓
Greeting + Nodding
↓
Dialog Playback
↓
Monitoring
```

---

# 2. Offline-First Rule

The entire system must operate offline.

Do not introduce:

```text
Cloud AI APIs

Online Face Recognition

Internet Dependencies

Online Authentication

Online Speech Services

Remote Processing
```

All processing must occur locally on Raspberry Pi.

---

# 3. Scope Protection Rule

The following technologies are permanently excluded from V3.

Do not implement:

```text
Whisper

Speech-To-Text

STT

Wake Words

Voice Commands

RNNoise

Voice Activity Detection

Language Detection

Conversational AI

Chat Engines

Scenario Engines

Question Answering

LLMs

Cloud Processing
```

Do not create experimental placeholders for these features.

---

# 4. Hardware Target Rule

Target hardware:

```text
Raspberry Pi 4

8 GB RAM

32 GB Storage

1.8 GHz CPU
```

All implementation decisions must prioritize:

```text
Low CPU Usage

Low Memory Usage

System Stability

Reliability

Long Runtime Operation
```

---

# 5. Face Recognition Priority Rule

Recognition accuracy is more important than frame rate.

Implementation priorities:

```text
Recognition Accuracy
↓
Recognition Stability
↓
Tracking Stability
↓
Greeting Reliability
↓
Servo Reliability
↓
Frame Rate
```

Do not reduce recognition quality solely to increase FPS.

---

# 6. Detection Technology Rule

Preferred face detection:

```text
MediaPipe Face Detection
```

Do not use:

```text
Haar Cascade

OpenCV Cascade Classifier

Legacy Dlib Face Detection
```

unless explicitly approved.

---

# 7. Recognition Technology Rule

Preferred face recognition:

```text
InsightFace

ArcFace Embeddings
```

The system shall not use:

```text
Dlib Face Recognition Embeddings
```

as the primary recognition engine.

---

# 8. Enrollment Rule

Every enrolled user shall support:

```text
Front Face

Left Face

Right Face
```

The system must not assume:

```text
Single Image Enrollment
```

is sufficient.

---

# 9. User Profile Rule

Every user record shall contain:

```text
User ID

Priority

Preferred Language

Embeddings

Greeting Audio Mapping

Dialog Audio Mapping
```

Do not store business logic in user records.

---

# 10. Multi-User Rule

The system must support:

```text
1 User

2 Users

3 Users

N Users
```

simultaneously.

Recognition must complete before greeting execution begins.

---

# 11. Priority Rule

Lower number means higher priority.

Example:

```text
Priority 1

Priority 2

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

This rule is mandatory.

Never reverse this behavior.

---

# 12. Equal Priority Rule

If users share the same priority:

Example:

```text
Manager Priority 1

Natnael Priority 1
```

Sort using:

```text
First Seen Timestamp
```

Rule:

```text
Earlier Detection
=
Higher Greeting Order
```

Avoid random ordering.

---

# 13. Greeting Persistence Rule

A user may only be greeted once during a presence session.

Example:

```text
User Appears
↓
Greeting Completes
↓
User Remains Visible
```

Result:

```text
No Additional Greeting
```

Repeated greetings are a defect.

---

# 14. Face Persistence Rule

Use:

```text
face_lost_timeout
```

before declaring user departure.

Temporary disappearance must not:

```text
Generate FACE_LOST

Replay Greetings

Restart Sessions

Reset Monitoring
```

---

# 15. Face Lost Rule

A user is considered lost only when:

```text
Visible
↓
Disappears
↓
Timeout Expires
```

Then:

```text
FACE_LOST
```

may be generated.

---

# 16. Audio Playback Rule

All audio playback must remain sequential.

Allowed:

```text
Audio A
↓
Audio B
↓
Audio C
```

Forbidden:

```text
Audio A
+
Audio B
```

simultaneously.

Audio overlap is not permitted.

---

# 17. Playback Ownership Rule

Audio playback shall be controlled only by:

```text
playback.py
```

Other modules must not:

```text
Directly Access Audio Devices
```

All playback requests shall go through the Playback Service.

---

# 18. Head Motion Rule

The robotic neck consists of:

```text
Yaw Servo

Pitch Servo
```

No additional body motors are part of V3.

---

# 19. Yaw Servo Rule

Yaw responsibilities:

```text
Surveillance Scanning

Face Tracking

User Following
```

Yaw must never perform:

```text
Greeting Nods
```

---

# 20. Surveillance Rule

When the system enters:

```text
FACE_DETECTION_MODE
```

Yaw shall perform:

```text
Left
↓
Center
↓
Right
↓
Center
```

continuous scanning.

---

# 21. Face Tracking Rule

When users are detected:

```text
Yaw Tracking
=
Enabled
```

Tracking priority:

```text
Highest Priority Visible User
```

If no priority conflict exists:

```text
Track Closest Visible User
```

is acceptable.

---

# 22. Pitch Servo Rule

Pitch responsibilities:

```text
Greeting Nodding
```

Pitch shall not perform:

```text
Surveillance

Continuous Tracking
```

---

# 23. Nodding Rule

Every greeting shall trigger:

```text
Greeting Audio
+
Nod Animation
```

The greeting and nod shall occur together.

---

# 24. Dialog Rule

Dialog playback must never trigger:

```text
Greeting Nodding
```

During dialogs:

```text
Yaw Tracking Active

Pitch Neutral
```

---

# 25. Interaction Mode Rule

Only two interaction modes exist.

---

## Mode A

```text
Greeting + Nod
↓
Greeting + Nod
↓
Greeting + Nod
↓
Common Dialog
```

---

## Mode B

```text
Greeting + Nod + Dialog
↓
Greeting + Nod + Dialog
↓
Greeting + Nod + Dialog
```

No additional modes may be introduced.

---

# 26. Dialog Interruption Rule

Dialog interruption is allowed only for:

```text
Dialog Playback
```

Never interrupt:

```text
Greetings
```

Requirements:

```text
Pause

Resume

Continue Playback
```

Resume must continue from:

```text
Stored Position
```

not the beginning.

---

# 27. Greeting Restart Rule

Dashboard shall provide:

```text
Restart Greetings
```

Behavior:

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

Restart Greetings shall not:

```text
Restart Application

Clear Enrollments

Remove Users
```

---

# 28. Dashboard Rule

Dashboard pages shall remain presentation-only.

Business logic must stay inside services.

Dashboard responsibilities:

```text
Display Status

Display Users

Display Servo Information

Change Settings

Issue Commands
```

---

# 29. FSM Ownership Rule

Only the FSM controls state transitions.

Modules must not directly force state changes.

Correct:

```text
Publish Event
↓
FSM Handles Transition
```

Incorrect:

```text
Module Changes FSM State Directly
```

---

# 30. Event Bus Rule

Component communication shall use:

```text
event_bus.py
```

Preferred:

```text
Publish Event
↓
Subscribe Event
↓
Handle Event
```

Avoid tight coupling.

---

# 31. State Manager Rule

Current state information shall only be maintained by:

```text
state_manager.py
```

Do not duplicate state storage elsewhere.

---

# 32. Event Naming Rule

Events must use:

```text
UPPER_CASE_NAMES
```

Examples:

```text
FACE_DETECTED

FACE_RECOGNIZED

FACE_LOST

PLAYBACK_FINISHED

GREETING_STARTED

GREETING_FINISHED

ALL_USERS_LOST

RESTART_GREETINGS
```

---

# 33. Logging Rule

The system shall log:

```text
State Changes

Recognition Events

Servo Events

Playback Events

Greeting Events

Errors

Warnings
```

Avoid excessive logging noise.

---

# 34. Error Handling Rule

The system must continue operating after:

```text
Missing Greeting Audio

Missing Dialog Audio

Missing User Profile

Playback Failure

Servo Failure

Camera Failure

Recognition Failure
```

All failures must be logged.

System crashes are unacceptable.

---

# 35. Module Ownership Rule

Responsibilities are fixed.

```text
camera_service.py
    Camera

face_recognition.py
    Detection + Recognition

face_presence_manager.py
    Presence Tracking

priority_manager.py
    Priority Sorting

greeting_manager.py
    Greeting Logic

head_motion_controller.py
    Servo Control

playback.py
    Audio Playback

fsm.py
    State Management

event_bus.py
    Event Distribution

state_manager.py
    State Storage

logger.py
    Logging

face_enrollment.py
    Enrollment
```

Do not mix responsibilities.

---

# 36. Code Quality Rule

Required:

✅ Type Hints

✅ Docstrings

✅ Small Functions

✅ Clear Naming

✅ Consistent Events

✅ Reusable Components

Avoid:

❌ Circular Imports

❌ Giant Functions

❌ Hidden Side Effects

❌ Global Mutable State

---

# 37. Documentation Rule

The following documents are authoritative:

```text
PROJECT_SPECIFICATION_V3.md

STATE_MACHINE_V3.md

SYSTEM_ARCHITECTURE_V3.md

HEAD_MOTION_SPECIFICATION_V3.md

AUDIO_STRUCTURE_V3.md

ACCEPTANCE_TESTS_V3.md

IMPLEMENTATION_GUIDE_V3.md

CLAUDE.md
```

If implementation differs:

```text
Documentation Wins
```

until documentation is formally updated.

---

# 38. Validation Rule

Every implementation must pass:

```text
ACCEPTANCE_TESTS_V3.md
```

before considered complete.

---

# 39. Final Development Rule

When facing multiple implementation options:

Prefer:

```text
Simplicity
↓
Maintainability
↓
Offline Operation
↓
Recognition Accuracy
↓
Raspberry Pi Compatibility
```

Avoid:

```text
Overengineering

Unspecified Features

Additional AI Features

Architectural Complexity
```

---

# 40. Definition of Success

EthioChatbot V3 is complete only when:

✅ Face Detection Works

✅ Face Recognition Works

✅ Multi-User Recognition Works

✅ Face Tracking Works

✅ Yaw Surveillance Works

✅ Greeting Nodding Works

✅ Priority Sorting Works

✅ Greeting Queue Works

✅ Mode A Works

✅ Mode B Works

✅ Dialog Interruption Works

✅ Restart Greetings Works

✅ Dashboard Works

✅ Monitoring Works

✅ Fully Offline Operation Works

✅ Raspberry Pi Deployment Works

---

# End of Document
