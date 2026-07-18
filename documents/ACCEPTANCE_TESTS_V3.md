# ACCEPTANCE_TESTS_V3.md

# EthioChatbot V3
## System Acceptance Test Specification

---

# Document Purpose

This document defines the official acceptance tests for EthioChatbot V3.

Acceptance tests verify that:

- Functional requirements are implemented correctly.
- Component interactions work correctly.
- System behavior matches the approved specifications.
- The system is ready for demonstration and deployment.

A feature is considered complete only when all applicable acceptance tests pass.

---

# Test Environment

## Hardware

```text
Raspberry Pi 4
8 GB RAM
32 GB Storage
1.8 GHz CPU
```

## Required Peripherals

```text
Camera
Speaker
Display (Optional)
```

## Required Software

```text
EthioChatbot V3
Configured Audio Files
Registered Users
```

---

# Test Categories

```text
A. System Startup

B. Face Detection

C. Face Recognition

D. Multi-User Recognition

E. Priority Processing

F. Greeting Playback

G. Interaction Mode A

H. Interaction Mode B

I. Face Persistence

J. Face Loss

K. Dialog Interruption

L. Dashboard

M. Recovery Tests

N. End-to-End Demonstration
```

---

# SECTION A
# System Startup Tests

---

## TEST A-01

### System Startup

Objective:

Verify application starts successfully.

Steps:

```text
Start application
```

Expected Result:

```text
System initializes successfully.

No startup errors.

Camera initializes successfully.

FSM enters:
FACE_DETECTION_MODE
```

Result:

```text
PASS / FAIL
```

---

## TEST A-02

### Configuration Loading

Objective:

Verify configuration files load correctly.

Steps:

```text
Start application.

Load settings.json.

Load interaction_modes.json.
```

Expected Result:

```text
Configuration loaded.

No exceptions.
```

Result:

```text
PASS / FAIL
```

---

# SECTION B
# Face Detection Tests

---

## TEST B-01

### Single Face Detection

Objective:

Verify one face can be detected.

Steps:

```text
Present one enrolled user.
```

Expected Result:

```text
FACE_DETECTED generated.
```

Result:

```text
PASS / FAIL
```

---

## TEST B-02

### Multiple Face Detection

Objective:

Verify multiple faces can be detected.

Steps:

```text
Present three enrolled users.
```

Expected Result:

```text
All visible faces detected.
```

Result:

```text
PASS / FAIL
```

---

## TEST B-03

### Side Face Detection

Objective:

Verify side-profile detection.

Steps:

```text
Show left profile.

Show right profile.
```

Expected Result:

```text
Face remains detectable.
```

Result:

```text
PASS / FAIL
```

---

# SECTION C
# Face Recognition Tests

---

## TEST C-01

### Single User Recognition

Objective:

Verify recognition of enrolled user.

Steps:

```text
Present enrolled user.
```

Expected Result:

```text
Correct user recognized.
```

Result:

```text
PASS / FAIL
```

---

## TEST C-02

### Front Face Recognition

Steps:

```text
Present front view.
```

Expected Result:

```text
Correct recognition.
```

Result:

```text
PASS / FAIL
```

---

## TEST C-03

### Left Side Recognition

Steps:

```text
Present left profile.
```

Expected Result:

```text
Correct recognition.
```

Result:

```text
PASS / FAIL
```

---

## TEST C-04

### Right Side Recognition

Steps:

```text
Present right profile.
```

Expected Result:

```text
Correct recognition.
```

Result:

```text
PASS / FAIL
```

---

# SECTION D
# Multi-User Recognition Tests

---

## TEST D-01

### Two Users

Steps:

```text
Present two enrolled users.
```

Expected Result:

```text
Both users recognized.
```

Result:

```text
PASS / FAIL
```

---

## TEST D-02

### Three Users

Steps:

```text
Present three enrolled users.
```

Expected Result:

```text
All users recognized.
```

Result:

```text
PASS / FAIL
```

---

## TEST D-03

### Five Users

Steps:

```text
Present five enrolled users.
```

Expected Result:

```text
All users recognized.
```

Result:

```text
PASS / FAIL
```

---

# SECTION E
# Priority Processing Tests

---

## TEST E-01

### Priority Sorting

Users:

```text
Manager  Priority 1
Natnael  Priority 2
Visitor  Priority 3
```

Expected Order:

```text
Manager
Natnael
Visitor
```

Result:

```text
PASS / FAIL
```

---

## TEST E-02

### Reverse Entry Order

Users appear:

```text
Visitor
Natnael
Manager
```

Expected Greeting Order:

```text
Manager
Natnael
Visitor
```

Result:

```text
PASS / FAIL
```

---

# SECTION F
# Greeting Playback Tests

---

## TEST F-01

### Single User Greeting

Steps:

```text
Present one user.
```

Expected Result:

```text
Greeting plays.
```

Result:

```text
PASS / FAIL
```

---

## TEST F-02

### Multiple User Greetings

Steps:

```text
Present three users.
```

Expected Result:

```text
Greeting 1
↓
Greeting 2
↓
Greeting 3
```

No overlap.

Result:

```text
PASS / FAIL
```

---

## TEST F-03

### Greeting Persistence

Steps:

```text
User greeted.

User remains visible.
```

Expected Result:

```text
Greeting not replayed.
```

Result:

```text
PASS / FAIL
```

---

# SECTION G
# Mode A Tests

---

## TEST G-01

### Common Dialog Mode

Configuration:

```json
{
  "interaction_mode": "common_dialog"
}
```

Expected Sequence:

```text
Greeting User 1
↓
Greeting User 2
↓
Greeting User 3
↓
Common Dialog
```

Result:

```text
PASS / FAIL
```

---

## TEST G-02

### Common Dialog Plays Once

Expected:

```text
One common dialog only.
```

Result:

```text
PASS / FAIL
```

---

# SECTION H
# Mode B Tests

---

## TEST H-01

### User Specific Dialog Mode

Configuration:

```json
{
  "interaction_mode": "user_specific_dialog"
}
```

Expected:

```text
Greeting User 1
↓
Dialog User 1

↓

Greeting User 2
↓
Dialog User 2
```

Result:

```text
PASS / FAIL
```

---

## TEST H-02

### User Dialog Mapping

Expected:

```text
Correct dialog file selected
for each user.
```

Result:

```text
PASS / FAIL
```

---

# SECTION I
# Face Persistence Tests

---

## TEST I-01

### Temporary Disappearance

Steps:

```text
User disappears.

Returns within 5 seconds.
```

Expected:

```text
No FACE_LOST.

No re-greeting.
```

Result:

```text
PASS / FAIL
```

---

## TEST I-02

### Presence Tracking

Expected:

```text
User remains active.
```

Result:

```text
PASS / FAIL
```

---

# SECTION J
# Face Loss Tests

---

## TEST J-01

### User Leaves

Steps:

```text
User disappears.

Remain absent > 5 seconds.
```

Expected:

```text
FACE_LOST generated.
```

Result:

```text
PASS / FAIL
```

---

## TEST J-02

### Reappearance

Steps:

```text
User leaves.

FACE_LOST generated.

User returns.
```

Expected:

```text
New greeting session.
```

Result:

```text
PASS / FAIL
```

---

## TEST J-03

### All Users Leave

Steps:

```text
All active users disappear.
```

Expected:

```text
ALL_USERS_LOST

↓

FACE_DETECTION_MODE
```

Result:

```text
PASS / FAIL
```

---

# SECTION K
# Dialog Interruption Tests

---

## TEST K-01

### Pause Dialog

Steps:

```text
Start dialog playback.

Pause playback.
```

Expected:

```text
Playback paused.
```

Result:

```text
PASS / FAIL
```

---

## TEST K-02

### Resume Dialog

Steps:

```text
Pause dialog.

Resume playback.
```

Expected:

```text
Playback continues from
same position.
```

Result:

```text
PASS / FAIL
```

---

## TEST K-03

### Greeting Interruption Protection

Steps:

```text
During greeting playback
attempt interruption.
```

Expected:

```text
Ignored.

Greeting completes.
```

Result:

```text
PASS / FAIL
```

---

# SECTION L
# Dashboard Tests

---

## TEST L-01

### Dashboard Loads

Expected:

```text
Dashboard opens successfully.
```

Result:

```text
PASS / FAIL
```

---

## TEST L-02

### Mode Switching

Steps:

```text
Switch Mode A

↓

Switch Mode B
```

Expected:

```text
Configuration updates correctly.
```

Result:

```text
PASS / FAIL
```

---

## TEST L-03

### System Status Display

Expected:

```text
Current State

Detected Users

Active Users

Playback Status
```

visible.

Result:

```text
PASS / FAIL
```

---

# SECTION M
# Recovery Tests

---

## TEST M-01

### Missing Greeting Audio

Expected:

```text
Error logged.

System continues running.
```

Result:

```text
PASS / FAIL
```

---

## TEST M-02

### Missing Dialog Audio

Expected:

```text
Error logged.

System continues running.
```

Result:

```text
PASS / FAIL
```

---

## TEST M-03

### Camera Disconnect

Expected:

```text
Error logged.

Recovery attempt performed.
```

Result:

```text
PASS / FAIL
```

---

# SECTION N
# End-to-End Demonstration Test

---

## TEST N-01

### Complete V3 Demonstration

Users:

```text
Manager
Natnael
Visitor
```

Expected Workflow:

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
↓
Dialog Playback
↓
MONITORING
↓
ALL_USERS_LOST
↓
FACE_DETECTION_MODE
```

Result:

```text
PASS / FAIL
```

---

# Acceptance Criteria

EthioChatbot V3 is accepted only if:

✅ All Critical Tests Pass

✅ No System Crashes

✅ Multi-User Greeting Passes

✅ Priority Sorting Passes

✅ Face Persistence Passes

✅ Face Loss Passes

✅ Mode A Passes

✅ Mode B Passes

✅ Dialog Interruption Passes

✅ Dashboard Passes

✅ Fully Offline Operation Passes

✅ Raspberry Pi Deployment Passes

---

# Final Approval

Project Status:

```text
☐ ACCEPTED

☐ REJECTED

☐ REQUIRES CORRECTION
```

Reviewer:

```text
_______________________
```

Date:

```text
_______________________
```

---

# End of Document
