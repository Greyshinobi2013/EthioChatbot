# PROJECT_SPECIFICATION_V3.md

# EthioChatbot V3
## Functional Project Specification

---

# Document Information

| Field | Value |
|---------|---------|
| Project Name | EthioChatbot V3 |
| System Type | Face Recognition Based Robotic Greeting System |
| Platform | Raspberry Pi 4 |
| Operation Mode | Fully Offline |
| Version | 3.0 |
| Status | Approved Specification |
| Purpose | Primary project specification |

---

# 1. Project Overview

EthioChatbot V3 is an offline robotic face-recognition-based multilingual greeting and information system.

The system continuously monitors its environment, detects and recognizes enrolled users, physically turns its head toward visible users, greets them according to priority, performs greeting nodding motions, and plays pre-recorded informational dialogs.

EthioChatbot V3 is intentionally designed without:

- Speech-to-Text (STT)
- Whisper
- Wake Words
- Voice Commands
- RNNoise
- VAD
- Language Detection
- Conversational AI
- Scenario Engines
- Internet Connectivity

The entire interaction model is based on:

```text
Face Detection
↓
Face Recognition
↓
Priority Sorting
↓
Greeting + Head Nodding
↓
Dialog Playback
↓
Monitoring
```

---

# 2. Project Objectives

The system shall:

1. Detect visible faces.
2. Recognize enrolled users.
3. Support multiple enrolled users simultaneously.
4. Track visible users with robotic head movement.
5. Greet users according to assigned priority.
6. Perform synchronized nodding during greetings.
7. Play language-specific greeting audio.
8. Play informational dialogs.
9. Support configurable playback modes.
10. Remain fully offline.
11. Operate reliably on Raspberry Pi 4.
12. Provide a realistic robotic interaction experience.

---

# 3. Hardware Platform

Target Hardware:

```text
Raspberry Pi 4
8GB RAM
32GB Storage
1.8 GHz CPU
```

Required Hardware:

```text
Camera
Speaker
Display (Optional)

Yaw Servo
Pitch Servo
```

---

# 4. Robotic Neck System

EthioChatbot V3 includes a robotic neck subsystem.

The neck contains:

```text
1 Horizontal Servo (Yaw)

1 Vertical Servo (Pitch)
```

---

## Yaw Servo

Purpose:

```text
Left and Right movement
```

Responsibilities:

```text
Environmental Surveillance

Face Tracking

User Following
```

---

## Pitch Servo

Purpose:

```text
Up and Down movement
```

Responsibilities:

```text
Greeting Nodding

Acknowledgement Motion
```

---

# 5. Technology Architecture

---

## Face Detection

Technology:

```text
MediaPipe Face Detection
```

Requirements:

```text
Real-Time

Multi-Face Support

Frontal Face Detection

Side Face Detection
```

---

## Face Recognition

Technology:

```text
InsightFace

ArcFace Embeddings
```

Requirements:

```text
High Accuracy

Stable Recognition

Multi-Angle Support
```

---

## Face Tracking

Technology:

```text
Centroid Tracking
```

Purpose:

```text
Track visible users efficiently
```

---

## Dashboard

Technology:

```text
Streamlit
```

Purpose:

```text
Administration

Enrollment

Configuration

Monitoring
```

---

# 6. Supported Languages

The system supports:

```text
English

Amharic

Arabic
```

Language comes from enrollment.

Example:

```json
{
  "preferred_language": "amharic"
}
```

No runtime language detection exists.

---

# 7. User Profile

Each user shall contain:

```json
{
  "user_id": "",
  "priority": 0,
  "preferred_language": "",
  "greeting_audio": "",
  "dialog_audio": ""
}
```

---

# 8. Enrollment Requirements

Each user must provide:

```text
Front Face

Left Face

Right Face
```

Purpose:

```text
Improve Recognition Quality

Improve Side Profile Recognition
```

Generated embeddings shall be stored for all captured angles.

---

# 9. Multi-User Recognition

The system must support:

```text
1 User

2 Users

3 Users

N Users
```

simultaneously.

All users shall be recognized before greeting begins.

---

# 10. Priority System

Every user shall have a priority value.

Rule:

```text
Lower Number
=
Higher Priority
```

Example:

```text
Manager    Priority 1

Natnael    Priority 2

Visitor    Priority 3
```

Greeting order:

```text
Manager
↓
Natnael
↓
Visitor
```

---

# 11. Head Movement Behavior

---

## Surveillance Scan

Active State:

```text
FACE_DETECTION_MODE
```

Behavior:

```text
Left
↓
Center
↓
Right
↓
Center
```

Continuously.

Purpose:

```text
Environmental surveillance
```

---

## Face Tracking

Active States:

```text
FACE_DETECTED

FACE_RECOGNIZED

MONITORING
```

Behavior:

```text
Yaw servo turns toward visible users.
```

Goal:

```text
Keep user near camera center.
```

---

## Greeting Nodding

Every greeting shall include:

```text
Greeting Audio
+
Pitch Servo Nodding
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

A nod shall occur for each greeting.

---

# 12. Greeting Rules

Greetings are played individually.

No overlapping playback allowed.

Example:

```text
Manager Greeting
↓
Natnael Greeting
↓
Visitor Greeting
```

Each greeting includes:

```text
Greeting Audio
+
Greeting Nod
```

---

# 13. Greeting Persistence

Users are greeted only once during a presence session.

Example:

```text
User Appears
↓
Greeting Played
↓
User Remains Visible
```

Result:

```text
No Additional Greeting
```

---

# 14. Interaction Modes

EthioChatbot V3 supports two interaction modes.

---

# Mode A

## Common Dialog Mode

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

Requirements:

```text
All greetings complete before common dialog begins.
```

During common dialog:

```text
Yaw Tracking Active

Pitch Neutral
```

---

# Mode B

## User Specific Dialog Mode

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

Example:

```text
Manager Greeting + Nod
↓
Manager Dialog

↓

Natnael Greeting + Nod
↓
Natnael Dialog

↓

Visitor Greeting + Nod
↓
Visitor Dialog
```

Requirements:

```text
Greeting always precedes dialog.
```

---

# 15. Dialog Interruption Framework

Purpose:

Future extensibility.

Current Scope:

```text
Pause Dialog

Resume Dialog

Continue Playback
```

Applies only to:

```text
Dialog Playback
```

Does NOT apply to:

```text
Greeting Playback
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
Continue From Saved Position
↓
Finish Playback
```

The dialog must never restart automatically.

---

# 16. Face Presence Management

Purpose:

Prevent false departures.

Configuration:

```json
{
  "face_lost_timeout": 5
}
```

---

## Temporary Disappearance

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

## Permanent Disappearance

```text
Face Missing
↓
5 Seconds Pass
```

Result:

```text
FACE_LOST
```

User removed from active list.

---

# 17. Monitoring Mode

After greetings and dialogs complete:

```text
MONITORING
```

Responsibilities:

```text
Track Users

Track Presence

Track Face Position
```

---

## Head Behavior During Monitoring

Yaw:

```text
Track User
```

Pitch:

```text
Neutral
```

---

# 18. Return To Detection Mode

When:

```text
ALL_USERS_LOST
```

Transition:

```text
FACE_DETECTION_MODE
```

Camera remains active.

System remains operational.

No restart required.

---

# 19. Dashboard Requirements

Dashboard must display:

```text
Current State

Detected Users

Active Users

Greeting Queue

Playback Status

Current Interaction Mode

Servo Status

Yaw Angle

Pitch Angle
```

Dashboard shall allow:

```text
Interaction Mode Switching

Restart Greetings

Pause Dialog

Resume Dialog

Center Head
```

---

# 20. Performance Goals

Target:

```text
Real-Time Face Detection

Accurate Face Recognition

Smooth Servo Motion

Reliable Playback

Multi-User Support
```

Priority:

```text
Recognition Accuracy
↓
Recognition Stability
↓
Greeting Reliability
↓
Servo Reliability
↓
Frame Rate
```

---

# 21. Out of Scope

The following are not part of EthioChatbot V3:

```text
Speech-To-Text

Whisper

Wake Words

Voice Commands

Language Detection

Conversational AI

Question Answering

Internet Access

Cloud Services

Full Body Motion
```

Only neck motion is supported.

---

# 22. Success Criteria

The project shall be considered complete when:

✅ Face Detection Works

✅ Face Recognition Works

✅ Multi-User Recognition Works

✅ Enrollment Works

✅ Priority Sorting Works

✅ Greeting Persistence Works

✅ Face Persistence Works

✅ Yaw Surveillance Scanning Works

✅ Face Tracking Works

✅ Greeting Nodding Works

✅ Mode A Works

✅ Mode B Works

✅ Dialog Interruption Works

✅ Dashboard Controls Work

✅ Fully Offline Operation Works

✅ Raspberry Pi Deployment Works

---

# Version

```text
EthioChatbot V3
Robotic Face Recognition Greeting System
```

---

# End of Document
