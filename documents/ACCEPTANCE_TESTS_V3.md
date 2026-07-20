# ACCEPTANCE_TESTS_V3.md

# EthioChatbot V3
## System Acceptance Test Specification

---

# Document Purpose

This document defines the official acceptance tests for EthioChatbot V3.

Acceptance tests verify:

- Face detection
- Face recognition
- Multi-user recognition
- Priority sorting
- Greeting workflow
- Head motion control
- Yaw tracking
- Greeting nodding
- Dialog playback
- Dialog interruption
- Monitoring
- Dashboard functionality

A feature is considered complete only when all applicable tests pass.

---

# Test Environment

## Hardware

```text
Raspberry Pi 4
8GB RAM
32GB Storage
1.8GHz CPU
```

---

## Required Hardware

```text
Camera

Speaker

Yaw Servo

Pitch Servo
```

---

## Software

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

G. Mode A

H. Mode B

I. Face Persistence

J. Face Loss

K. Dialog Interruption

L. Dashboard

M. Error Recovery

N. End-To-End Demonstration

O. Head Motion System
```

---

# SECTION A
# System Startup

---

## TEST A-01
### Application Startup

Objective:

Verify successful startup.

Steps:

```text
Launch application
```

Expected:

```text
Configuration Loaded

Camera Initialized

Face Recognition Initialized

Head Motion Controller Initialized

FSM Initialized

Dashboard Available

State:
FACE_DETECTION_MODE
```

Result:

```text
PASS / FAIL
```

---

## TEST A-02
### Configuration Loading

Steps:

```text
Start system
```

Expected:

```text
settings.json loaded

No configuration errors
```

Result:

```text
PASS / FAIL
```

---

# SECTION B
# Face Detection

---

## TEST B-01
### Single Face Detection

Steps:

```text
Present one face
```

Expected:

```text
Face detected successfully
```

Result:

```text
PASS / FAIL
```

---

## TEST B-02
### Multiple Face Detection

Steps:

```text
Present three users
```

Expected:

```text
All visible faces detected
```

Result:

```text
PASS / FAIL
```

---

## TEST B-03
### Left Side Face Detection

Steps:

```text
Show left profile
```

Expected:

```text
Face detected
```

Result:

```text
PASS / FAIL
```

---

## TEST B-04
### Right Side Face Detection

Steps:

```text
Show right profile
```

Expected:

```text
Face detected
```

Result:

```text
PASS / FAIL
```

---

# SECTION C
# Face Recognition

---

## TEST C-01
### Front Recognition

Expected:

```text
Correct user recognized
```

Result:

```text
PASS / FAIL
```

---

## TEST C-02
### Left Profile Recognition

Expected:

```text
Correct user recognized
```

Result:

```text
PASS / FAIL
```

---

## TEST C-03
### Right Profile Recognition

Expected:

```text
Correct user recognized
``

Result:

```text
PASS / FAIL
```

---

## TEST C-04
### Unknown Face

Steps:

```text
Present non-enrolled user
```

Expected:

```text
No match returned
```

Result:

```text
PASS / FAIL
```

---

# SECTION D
# Multi-User Recognition

---

## TEST D-01
### Two Users

Expected:

```text
Both users recognized
```

Result:

```text
PASS / FAIL
```

---

## TEST D-02
### Three Users

Expected:

```text
All three users recognized
```

Result:

```text
PASS / FAIL
```

---

## TEST D-03
### Five Users

Expected:

```text
All visible users recognized
```

Result:

```text
PASS / FAIL
```

---

# SECTION E
# Priority Processing

---

## TEST E-01
### Priority Sorting

Users:

```text
Manager   Priority 1

Natnael   Priority 2

Visitor   Priority 3
```

Expected:

```text
Manager
↓
Natnael
↓
Visitor
```

Result:

```text
PASS / FAIL
```

---

## TEST E-02
### Detection Order Does Not Matter

Arrival Order:

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

## TEST E-03
### Equal Priority Users

Users:

```text
User A Priority 1

User B Priority 1
```

Expected:

```text
First detected user greeted first
```

Result:

```text
PASS / FAIL
```

---

# SECTION F
# Greeting Playback

---

## TEST F-01
### Single User Greeting

Expected:

```text
Greeting audio plays
```

Result:

```text
PASS / FAIL
```

---

## TEST F-02
### Multi-User Greeting

Expected:

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

Expected:

```text
Greeting occurs once per session
```

Result:

```text
PASS / FAIL
```

---

# SECTION G
# Mode A

---

## TEST G-01
### Common Dialog Workflow

Expected:

```text
Greeting + Nod
↓
Greeting + Nod
↓
Greeting + Nod
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
One common dialog playback
```

Result:

```text
PASS / FAIL
```

---

## TEST G-03
### Common Dialog Completion

Expected:

```text
MONITORING state entered
```

Result:

```text
PASS / FAIL
```

---

# SECTION H
# Mode B

---

## TEST H-01
### User Dialog Workflow

Expected:

```text
Greeting + Nod + Dialog
↓
Greeting + Nod + Dialog
↓
Greeting + Nod + Dialog
```

Result:

```text
PASS / FAIL
```

---

## TEST H-02
### Dialog Mapping

Expected:

```text
Correct dialog selected
for each user
```

Result:

```text
PASS / FAIL
```

---

# SECTION I
# Face Persistence

---

## TEST I-01
### Temporary Face Loss

Steps:

```text
Face disappears

Returns within timeout
```

Expected:

```text
No FACE_LOST

No re-greeting
```

Result:

```text
PASS / FAIL
```

---

## TEST I-02
### Active User Retention

Expected:

```text
User remains active
```

Result:

```text
PASS / FAIL
```

---

# SECTION J
# Face Loss

---

## TEST J-01
### Permanent Loss

Steps:

```text
Face disappears

Timeout expires
```

Expected:

```text
FACE_LOST generated
```

Result:

```text
PASS / FAIL
```

---

## TEST J-02
### User Returns

Steps:

```text
FACE_LOST
↓
User returns
```

Expected:

```text
New greeting session
```

Result:

```text
PASS / FAIL
```

---

## TEST J-03
### All Users Leave

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
# Dialog Interruption

---

## TEST K-01
### Pause Dialog

Expected:

```text
Dialog pauses
```

Result:

```text
PASS / FAIL
```

---

## TEST K-02
### Resume Dialog

Expected:

```text
Playback resumes
from stored position
```

Result:

```text
PASS / FAIL
```

---

## TEST K-03
### Greeting Protection

Expected:

```text
Greetings cannot be interrupted
```

Result:

```text
PASS / FAIL
```

---

## TEST K-04
### Restart Greetings While Dialog Paused

Steps:

```text
Pause dialog

Click Restart Greetings
```

Expected:

```text
Greeting queue rebuilt

Greetings replayed

Dialogs replayed
```

Result:

```text
PASS / FAIL
```

---

# SECTION L
# Dashboard

---

## TEST L-01
### Dashboard Loads

Expected:

```text
Dashboard visible
```

Result:

```text
PASS / FAIL
```

---

## TEST L-02
### Mode Switching

Expected:

```text
Mode A

↓

Mode B

saved correctly
```

Result:

```text
PASS / FAIL
```

---

## TEST L-03
### System Information

Expected:

```text
Current State

Detected Users

Active Users

Playback Status
```

Displayed.

Result:

```text
PASS / FAIL
```

---

## TEST L-04
### Servo Information

Expected:

```text
Yaw Position

Pitch Position

Servo Status
```

Displayed.

Result:

```text
PASS / FAIL
```

---

# SECTION M
# Error Recovery

---

## TEST M-01
### Missing Greeting Audio

Expected:

```text
Error logged

Application continues
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
Error logged

Application continues
```

Result:

```text
PASS / FAIL
```

---

## TEST M-03
### Servo Failure

Expected:

```text
Error logged

Application remains running
```

Result:

```text
PASS / FAIL
```

---

## TEST M-04
### Camera Failure

Expected:

```text
Error logged

Recovery attempted
```

Result:

```text
PASS / FAIL
```

---

# SECTION N
# End-To-End Demonstration

---

## TEST N-01
### Full Demonstration

Users:

```text
Manager

Natnael

Visitor
```

Expected:

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
PLAY_COMMON_DIALOG
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

# SECTION O
# Head Motion System

---

## TEST O-01
### Surveillance Scan

FSM State:

```text
FACE_DETECTION_MODE
```

Expected:

```text
Yaw scans

Left
↓
Center
↓
Right
↓
Center
```

Result:

```text
PASS / FAIL
```

---

## TEST O-02
### Stop Scan On Face Detection

Expected:

```text
Scan stops

Face tracking starts
```

Result:

```text
PASS / FAIL
```

---

## TEST O-03
### Face Tracking

Steps:

```text
Move user left

Move user right
```

Expected:

```text
Yaw follows user
```

Result:

```text
PASS / FAIL
```

---

## TEST O-04
### Greeting Nodding

Steps:

```text
Play greeting
```

Expected:

```text
Greeting audio
+
Pitch nod
```

occur together.

Result:

```text
PASS / FAIL
```

---

## TEST O-05
### Mode A Head Behavior

Expected:

```text
Greeting + Nod
↓
Greeting + Nod
↓
Greeting + Nod
↓
Common Dialog
```

During common dialog:

```text
Yaw tracking active

Pitch neutral
```

Result:

```text
PASS / FAIL
```

---

## TEST O-06
### Mode B Head Behavior

Expected:

```text
Greeting + Nod + Dialog
↓
Greeting + Nod + Dialog
↓
Greeting + Nod + Dialog
```

Dialog:

```text
Yaw tracking active

Pitch neutral
```

Result:

```text
PASS / FAIL
```

---

## TEST O-07
### Head Centering

Steps:

```text
Click Center Head
```

Expected:

```text
Yaw = Center

Pitch = Center
```

Result:

```text
PASS / FAIL
```

---

## TEST O-08
### Pause Dialog During Tracking

Steps:

```text
Start dialog

Pause dialog
```

Expected:

```text
Dialog paused

Yaw tracking continues

Pitch neutral
```

Result:

```text
PASS / FAIL
```

---

# Acceptance Criteria

EthioChatbot V3 is accepted only if:

✅ Face Detection Passes

✅ Face Recognition Passes

✅ Multi-User Recognition Passes

✅ Priority Sorting Passes

✅ Greeting Persistence Passes

✅ Face Persistence Passes

✅ Mode A Passes

✅ Mode B Passes

✅ Dialog Interruption Passes

✅ Restart Greetings Passes

✅ Dashboard Passes

✅ Yaw Scanning Passes

✅ Face Tracking Passes

✅ Greeting Nodding Passes

✅ Servo Controls Pass

✅ Raspberry Pi Deployment Passes

✅ Fully Offline Operation Passes

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
_________________________
```

Date:

```text
_________________________
```

---

# End of Document
