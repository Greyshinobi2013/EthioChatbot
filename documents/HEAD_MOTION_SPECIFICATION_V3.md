# HEAD_MOTION_SPECIFICATION_V3.md

# EthioChatbot V3
## Head Motion Control System Specification

---

# Purpose

This document defines the robotic neck motion system used by EthioChatbot V3.

The purpose of the neck system is to:

- Increase realism
- Provide active surveillance behavior
- Track visible users
- Perform greeting gestures
- Improve user engagement

---

# Hardware Configuration

The neck contains two servo motors.

## Horizontal Servo

Name:

```text
Yaw Servo
```

Purpose:

```text
Left / Right rotation
```

Responsibilities:

- Area surveillance
- Face tracking
- User following

---

## Vertical Servo

Name:

```text
Pitch Servo
```

Purpose:

```text
Up / Down movement
```

Responsibilities:

- Greeting nodding
- Future acknowledgement gestures

---

# Yaw Servo Functions

## Surveillance Scan

Active State:

```text
FACE_DETECTION_MODE
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

## Face Tracking

Active States:

```text
FACE_DETECTED

FACE_RECOGNIZED

MONITORING
```

Requirement:

```text
Keep highest-priority active user
approximately centered.
```

---

# Pitch Servo Functions

## Greeting Nodding

Active State:

```text
PLAY_GREETINGS
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

Requirements:

- Start with greeting playback
- Stop after greeting playback
- One nod sequence per greeting

---

# Interaction Modes

## Mode A

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

Pitch nodding occurs during greetings only.

No nodding during common dialog.

---

## Mode B

Workflow:

```text
Greeting + Nod + User Dialog
↓
Greeting + Nod + User Dialog
↓
Greeting + Nod + User Dialog
```

Pitch nodding occurs only during greetings.

No nodding during user dialogs.

---

# Monitoring Behavior

Yaw:

```text
Track active user
```

Pitch:

```text
Neutral
```

---

# Dialog Interruption

Dialog interruption must not affect servos.

Example:

```text
Dialog Paused
```

Result:

```text
Pitch remains neutral
Yaw tracking continues
```

---

# Future Expansion

Reserved for:

- Touch controls
- Gesture controls
- Voice controls
- Remote control interface

---

# End of Document

