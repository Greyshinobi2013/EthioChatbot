# PROJECT_SPECIFICATION_V3.md

# EthioChatbot V3
## Functional Project Specification

---

# Document Information

| Field | Value |
|---------|---------|
| Project Name | EthioChatbot V3 |
| System Type | Face Recognition-Based Multilingual Greeting System |
| Platform | Raspberry Pi 4 |
| Operation Mode | Fully Offline |
| Version | 3.0 |
| Status | Approved Specification |
| Purpose | Primary implementation specification for development |

---

# 1. Project Overview

EthioChatbot V3 is a face-recognition-based multilingual greeting and information system.

The system continuously monitors a camera feed, detects registered users, recognizes them, applies priority-based greeting logic, and plays pre-recorded audio interactions.

EthioChatbot V3 is intentionally designed without:

- Speech-to-Text (STT)
- Voice Commands
- Wake Words
- Language Detection
- Conversational AI
- Whisper
- VAD
- RNNoise
- Large Language Models (LLMs)

The entire interaction model is based on:

```text
Face Detection
↓
Face Recognition
↓
Priority Evaluation
↓
Greeting Playback
↓
Dialog Playback
↓
Monitoring
```

---

# 2. Project Objectives

The system shall:

1. Detect faces continuously.
2. Recognize enrolled users.
3. Support simultaneous recognition of multiple users.
4. Greet users according to priority.
5. Play pre-recorded audio using the enrolled language.
6. Support configurable interaction modes.
7. Prevent duplicate greetings during continuous presence.
8. Track face presence reliably.
9. Operate completely offline.
10. Run efficiently on Raspberry Pi 4 hardware.

---

# 3. Hardware Requirements

Target deployment platform:

```text
Raspberry Pi 4
8 GB RAM
32 GB Storage
1.8 GHz CPU
```

Required peripherals:

```text
HD Camera
Speaker
Display (optional)
Keyboard (optional)
Mouse (optional)
```

---

# 4. Technology Architecture

## Face Detection

Purpose:

```text
Locate faces in camera frames.
```

Selected Technology:

```text
MediaPipe Face Detection
```

Requirements:

- Real-time performance
- Multi-face detection
- Front-face support
- Side-face support
- Lightweight CPU usage

---

## Face Recognition

Purpose:

```text
Recognize enrolled users.
```

Selected Technology:

```text
InsightFace
ArcFace Embeddings
```

Requirements:

- High recognition accuracy
- Multi-angle matching
- Robust lighting tolerance
- Multiple registered users

---

## Face Tracking

Purpose:

```text
Maintain face identity between frames.
```

Selected Technology:

```text
Centroid Tracking
```

Requirements:

- Lightweight
- Stable tracking IDs
- Reduced recognition frequency

---

## Dashboard

Selected Technology:

```text
Streamlit
```

Dashboard provides:

- System status
- Active users
- Detected users
- Interaction mode
- Greeting queue
- Playback status

---

# 5. Supported Languages

EthioChatbot V3 supports:

```text
English
Amharic
Arabic
```

Language is determined during enrollment.

Example:

```json
{
  "preferred_language": "amharic"
}
```

No runtime language detection exists.

---

# 6. User Profile

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

# 7. Enrollment Requirements

Each user shall be enrolled with:

## Required Images

```text
Front Face
Left Face
Right Face
```

Purpose:

```text
Improve recognition quality.
Improve side-profile recognition.
```

Generated data:

```text
Face Embeddings
```

stored in:

```text
faces/embeddings/
```

---

# 8. Priority System

Each user shall be assigned a priority value.

Example:

```text
Priority 1
Priority 2
Priority 3
```

Rule:

```text
Lower Number = Higher Priority
```

Example:

```text
Manager  Priority 1
Natnael  Priority 2
Visitor  Priority 3
```

Processing order:

```text
Manager
↓
Natnael
↓
Visitor
```

---

# 9. Multi-User Support

The system shall support:

```text
1 User
2 Users
3 Users
N Users
```

simultaneously.

Example:

```text
Manager
Natnael
Visitor
```

All users shall be recognized before greetings begin.

---

# 10. Greeting Rules

## Greeting Sequence

Users shall be greeted sequentially.

Example:

```text
Manager Greeting
↓
Natnael Greeting
↓
Visitor Greeting
```

Requirements:

- No simultaneous audio.
- One greeting at a time.
- Respect priority ordering.

---

## Greeting Persistence

A user shall only be greeted once per presence session.

Example:

```text
User appears
↓
Greeting played
↓
User remains visible
```

Result:

```text
No repeated greeting.
```

---

# 11. Interaction Modes

The dashboard shall support two interaction modes.

---

## Mode A (Default)

Configuration:

```json
{
  "interaction_mode": "common_dialog"
}
```

Workflow:

```text
Greeting User 1
↓
Greeting User 2
↓
Greeting User 3
↓
Play One Common Dialog
```

Example:

```text
Manager Greeting
↓
Natnael Greeting
↓
Visitor Greeting
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

Workflow:

```text
Greeting User
↓
User Dialog

↓

Greeting User
↓
User Dialog
```

Example:

```text
Manager Greeting
↓
Manager Dialog

↓

Natnael Greeting
↓
Natnael Dialog
```

---

# 12. Dialog Playback Interruption

Purpose:

Provide a placeholder framework for future interaction features.

---

## Scope

Applicable only to:

```text
Dialog Playback
```

Not applicable to:

```text
Greetings
```

---

## Supported Actions

```text
Pause
Resume
Continue Playback
```

---

## Requirements

If dialog playback is interrupted:

```text
Dialog Playing
↓
Pause
↓
Resume
↓
Continue From Previous Position
↓
Playback Finished
```

The dialog must NOT restart from the beginning.

---

## Future Expansion

Future versions may trigger interruption using:

```text
Dashboard Controls
Physical Buttons
Touch Screens
Voice Controls
Remote APIs
```

V3 only provides the playback framework.

---

# 13. Face Presence Tracking

Purpose:

Prevent false departures.

Configuration:

```json
{
  "face_lost_timeout": 5
}
```

---

## Temporary Face Loss

Example:

```text
Face disappears
↓
Returns within 5 seconds
```

Result:

```text
No FACE_LOST event.
```

---

## Permanent Face Loss

Example:

```text
Face disappears
↓
5 seconds pass
```

Result:

```text
FACE_LOST
```

User removed from active list.

---

# 14. Monitoring Mode

After greetings and dialogs:

```text
MONITORING
```

The system:

- Continues tracking faces.
- Maintains active users.
- Waits for new users.
- Plays no additional audio.

---

# 15. Return to Detection Mode

When all users are gone:

```text
ALL_USERS_LOST
↓
FACE_DETECTION_MODE
```

Requirements:

- Camera remains active.
- System remains operational.
- No restart required.

---

# 16. State Machine Overview

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

Mode A
↓
PLAY_COMMON_DIALOG

Mode B
↓
PLAY_USER_DIALOGS

↓

MONITORING

↓

ALL_USERS_LOST

↓

FACE_DETECTION_MODE
```

---

# 17. Dashboard Requirements

Dashboard shall display:

```text
Current State

Detected Users

Active Users

Greeting Queue

Recognition Status

Playback Status

Interaction Mode

Face Presence Status
```

Dashboard shall allow:

```text
Switch Mode A / Mode B
```

without code changes.

---

# 18. Performance Goals

Target performance:

```text
Face Detection      Real-Time
Recognition Delay   < 2 Seconds
Greeting Start      < 1 Second
Multi-User Support  5+ Users
```

Priority:

```text
Recognition Accuracy
↑
Recognition Stability
↑
Playback Reliability
↑
Frame Rate
```

---

# 19. Out of Scope

The following are intentionally excluded:

```text
Speech-to-Text
Wake Words
Voice Commands
Whisper
RNNoise
Language Detection
Conversational AI
Question Answering
Scenario Engines
Internet Connectivity
Cloud Services
```

---

# 20. Success Criteria

EthioChatbot V3 shall be considered complete when:

✅ Face detection works.

✅ Face recognition works.

✅ Multi-user recognition works.

✅ Priority sorting works.

✅ Greeting persistence works.

✅ Face persistence works.

✅ Mode A works.

✅ Mode B works.

✅ Dialog interruption works.

✅ Dashboard switching works.

✅ Monitoring mode works.

✅ Return to detection mode works.

✅ Application runs fully offline on Raspberry Pi 4.

---

# End of Specification
