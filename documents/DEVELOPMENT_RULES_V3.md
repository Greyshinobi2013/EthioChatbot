# DEVELOPMENT_RULES_V3.md

# EthioChatbot V3
## Development Rules and Implementation Constraints

---

# Document Purpose

This document defines the mandatory development rules for EthioChatbot V3.

These rules must be followed by:

- Claude Code
- Developers
- Contributors
- Future maintainers

This document exists to prevent:

- Scope creep
- Architecture drift
- Unnecessary complexity
- Reintroduction of removed V2 features

All implementations must comply with these rules.

---

# 1. Primary Goal

EthioChatbot V3 is a:

```text
Face Recognition
+
Priority-Based Greeting
+
Multilingual Information Playback System
```

It is NOT a conversational chatbot.

The architecture must remain:

```text
Simple
Deterministic
Offline
Maintainable
Raspberry Pi Friendly
```

---

# 2. Preserve Existing Working Components

The following components are considered core system assets.

Reuse them whenever possible.

Do not rewrite them unless absolutely necessary.

### Approved Core Components

```text
camera_service.py

face_recognition.py

face_enrollment.py

event_bus.py

fsm.py

state_manager.py

playback.py

logger.py
```

---

# 3. Single Responsibility Principle

Every module must have one responsibility.

Examples:

```text
Face Recognition
    → Recognition only

Playback
    → Playback only

Priority Manager
    → Priority ordering only

FSM
    → State management only
```

Avoid placing unrelated logic in a module.

---

# 4. Event-Driven Design

EthioChatbot V3 shall remain event-driven.

Components must communicate using:

```text
Event Bus
```

Preferred flow:

```text
Publish Event
↓
Subscribe Event
↓
React
```

Avoid direct component coupling.

---

# 5. No Conversational Features

The following features are prohibited.

Do NOT implement:

```text
Speech-to-Text

Whisper

RNNoise

Voice Activity Detection (VAD)

Wake Words

Language Detection

Conversational AI

Question Answering

Scenario Engines

Chat Logic

Voice Commands
```

These features belong to EthioChatbot V2.

They are intentionally excluded from V3.

---

# 6. No Cloud Dependencies

EthioChatbot V3 must remain fully offline.

Do NOT introduce:

```text
Cloud APIs

Remote AI Models

Internet Requirements

External Processing Services

Online Authentication
```

All processing must occur locally.

---

# 7. Raspberry Pi Optimization Rules

Target Hardware:

```text
Raspberry Pi 4

8GB RAM
32GB Storage
1.8GHz CPU
```

All implementations must be optimized for this hardware.

Prioritize:

```text
Low CPU Use

Low Memory Use

Fast Startup

Fast Recognition

Stable Long-Term Runtime
```

Avoid unnecessary heavy libraries.

---

# 8. Face Recognition Rules

The system exists primarily for face recognition.

Recognition quality is more important than frame rate.

Preferred priorities:

```text
Recognition Accuracy
↓
Recognition Stability
↓
Playback Reliability
↓
Frame Rate
```

---

# 9. Multi-Angle Enrollment Rule

Every user should support:

```text
Front Face

Left Face

Right Face
```

Recognition code should be designed with multi-angle support in mind.

Never assume:

```text
One Face Image
```

is sufficient.

---

# 10. Priority Rules

Lower priority number means higher importance.

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

This rule must never be reversed.

---

# 11. Multi-User Processing Rule

The system must support:

```text
1 User

2 Users

3 Users

N Users
```

simultaneously.

Recognition must complete before greeting begins.

Do not start greeting while discovery is still occurring.

---

# 12. Sequential Audio Rule

Audio playback must always be sequential.

Allowed:

```text
Audio 1
↓
Audio 2
↓
Audio 3
```

Not Allowed:

```text
Audio 1 + Audio 2 simultaneously
```

No overlapping playback.

---

# 13. Greeting Persistence Rule

A user may only be greeted once during a presence session.

Example:

```text
User Detected
↓
Greeting Played
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

before declaring a user absent.

Temporary disappearance must not:

```text
Trigger FACE_LOST

Trigger Re-Greeting

Reset The Session
```

---

# 15. Interaction Modes

Only two interaction modes are permitted.

### Mode A

```text
All Greetings
↓
One Common Dialog
```

Configuration:

```json
{
  "interaction_mode": "common_dialog"
}
```

---

### Mode B

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

No additional interaction modes shall be introduced.

---

# 16. Dashboard Configuration Rule

The dashboard is the only place where administrators should modify runtime behavior.

Examples:

```text
Interaction Mode

Face Lost Timeout

System Settings
```

Avoid hard-coded values whenever configuration is appropriate.

---

# 17. Dialog Interruption Rule

Dialog interruption exists as a future-ready placeholder.

Current scope:

```text
Pause Dialog

Resume Dialog

Continue From Previous Position
```

Applies only to:

```text
Dialog Playback
```

Never interrupt:

```text
Greeting Audio
```

Greetings must always finish.

---

# 18. Playback Rules

Playback service is the only component allowed to control audio.

Do not duplicate playback functionality elsewhere.

Use:

```text
playback.py
```

for:

```text
Play

Pause

Resume

Stop

Status
```

---

# 19. FSM Ownership Rule

The FSM owns state transitions.

Other modules must not manually change system state.

Correct:

```text
Publish Event
↓
FSM Transition
```

Incorrect:

```text
Random Module
↓
Direct State Change
```

---

# 20. State Manager Rule

Current state information must be stored only in:

```text
state_manager.py
```

Do not duplicate state tracking.

---

# 21. Event Naming Rule

Event names must be:

```text
UPPER_CASE
```

Examples:

```text
FACE_DETECTED

FACE_RECOGNIZED

FACE_LOST

GREETING_STARTED

GREETING_FINISHED

PLAYBACK_STARTED

PLAYBACK_FINISHED

ALL_USERS_LOST
```

---

# 22. Logging Rule

Important system actions must be logged.

Log:

```text
State Changes

Recognition Events

Playback Events

Errors

Warnings
```

Avoid excessive debug spam.

---

# 23. Error Handling Rule

The system must never crash because:

```text
Missing Audio File

Invalid User

Missing Embedding

Playback Failure
```

Fallback behavior must exist.

All failures should be logged.

---

# 24. Dashboard Rule

Dashboard pages must remain focused.

Pages:

```text
Dashboard

Enrollment

Settings
```

Do not place implementation logic inside dashboard pages.

Dashboard pages should call services.

---

# 25. File Ownership Rule

Module ownership:

```text
camera_service.py
    Camera

face_recognition.py
    Recognition

face_presence_manager.py
    Presence Tracking

priority_manager.py
    User Ordering

greeting_manager.py
    Greeting Logic

playback.py
    Audio

fsm.py
    State Machine

state_manager.py
    State Storage

event_bus.py
    Events

logger.py
    Logging
```

Do not mix responsibilities.

---

# 26. Code Quality Rules

Required:

✅ Type hints

✅ Clear docstrings

✅ Consistent naming

✅ Small reusable functions

✅ Dependency injection where appropriate

Avoid:

❌ Large monolithic functions

❌ Global mutable state

❌ Hidden side effects

❌ Circular imports

---

# 27. Repository Rules

Documents inside:

```text
documents/
```

are authoritative.

Implementation must follow:

```text
PROJECT_SPECIFICATION_V3.md

STATE_MACHINE_V3.md

SYSTEM_ARCHITECTURE_V3.md

AUDIO_STRUCTURE_V3.md

ACCEPTANCE_TESTS_V3.md

DEVELOPMENT_RULES_V3.md
```

If code and documentation conflict:

```text
Documentation Wins
```

until officially updated.

---

# 28. Success Criteria

Implementation shall be considered complete only when:

✅ Face recognition works.

✅ Multi-user recognition works.

✅ Priority ordering works.

✅ Greeting persistence works.

✅ Face persistence works.

✅ Mode A works.

✅ Mode B works.

✅ Dialog interruption works.

✅ Dashboard switching works.

✅ Monitoring mode works.

✅ Return to detection mode works.

✅ Fully offline operation works.

✅ Raspberry Pi deployment succeeds.

---

# Final Rule

When a design decision is unclear:

```text
Prefer Simplicity

Prefer Offline

Prefer Maintainability

Prefer Raspberry Pi Performance

Avoid Unnecessary Complexity
```

---

# End of Document
