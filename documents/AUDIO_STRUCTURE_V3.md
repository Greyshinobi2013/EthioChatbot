# AUDIO_STRUCTURE_V3.md

# EthioChatbot V3
## Audio Architecture and Playback Structure Specification

---

# Document Purpose

This document defines the official audio structure for EthioChatbot V3.

It specifies:

- Audio directory layout
- Naming conventions
- Greeting audio structure
- Dialog audio structure
- Interaction modes
- Playback sequencing
- Language mapping
- Future extensibility

This document is the authoritative source for all audio-related implementation.

---

# Design Goals

The audio subsystem shall be:

```text
Simple
Predictable
Deterministic
Offline
Maintainable
Extensible
```

The audio subsystem must support:

```text
Single User Interaction

Multi-User Interaction

Priority-Based Greetings

Mode A

Mode B

Playback Interruption Framework
```

---

# Audio Root Structure

```text
audio/
│
├── english/
│   ├── greetings/
│   └── dialogs/
│
├── amharic/
│   ├── greetings/
│   └── dialogs/
│
├── arabic/
│   ├── greetings/
│   └── dialogs/
│
└── common/
```

---

# Supported Languages

EthioChatbot V3 supports:

```text
English
Amharic
Arabic
```

Each language has its own audio resources.

Language selection comes from:

```text
User Enrollment Profile
```

Example:

```json
{
    "preferred_language": "amharic"
}
```

No runtime language detection exists.

---

# Language Folder Structure

## English

```text
audio/
└── english/
    ├── greetings/
    └── dialogs/
```

---

## Amharic

```text
audio/
└── amharic/
    ├── greetings/
    └── dialogs/
```

---

## Arabic

```text
audio/
└── arabic/
    ├── greetings/
    └── dialogs/
```

---

# Greetings Directory

Purpose:

```text
Store greeting audio files
for enrolled users.
```

Structure:

```text
greetings/
```

Example:

```text
audio/english/greetings/

manager.wav
natnael.wav
visitor.wav
```

---

# Greeting Naming Convention

Format:

```text
<user_id>.wav
```

Examples:

```text
manager.wav

natnael.wav

visitor.wav

admin.wav
```

Requirements:

```text
One greeting file per user.
```

---

# Greeting Language Mapping

Example:

```text
audio/
└── amharic/
    └── greetings/
        └── natnael.wav
```

Enrollment:

```json
{
    "user_id": "natnael",
    "preferred_language": "amharic"
}
```

Playback:

```text
natnael.wav
```

from:

```text
audio/amharic/greetings/
```

---

# Dialog Directory

Purpose:

```text
Store informational audio
played after greeting sequences.
```

Directory:

```text
dialogs/
```

---

# Interaction Modes

EthioChatbot V3 supports:

```text
Mode A

Mode B
```

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
Greeting User 1
↓
Greeting User 2
↓
Greeting User 3
↓
Common Dialog
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

## Mode A Audio Structure

```text
audio/

english/
└── dialogs/
    └── common_dialog.wav

amharic/
└── dialogs/
    └── common_dialog.wav

arabic/
└── dialogs/
    └── common_dialog.wav
```

---

## Mode A Playback Rules

Requirements:

```text
Play all greetings first.
```

After the final greeting:

```text
Play one common dialog.
```

Then:

```text
Enter Monitoring Mode.
```

---

# Mode B

## User-Specific Dialog Mode

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
Dialog User

↓

Greeting User
↓
Dialog User

↓

Greeting User
↓
Dialog User
```

---

## Mode B Audio Structure

```text
audio/

english/
└── dialogs/
    ├── manager.wav
    ├── natnael.wav
    └── visitor.wav

amharic/
└── dialogs/
    ├── manager.wav
    ├── natnael.wav
    └── visitor.wav

arabic/
└── dialogs/
    ├── manager.wav
    ├── natnael.wav
    └── visitor.wav
```

---

## Mode B Naming Convention

Format:

```text
<user_id>.wav
```

Examples:

```text
manager.wav

natnael.wav

visitor.wav
```

---

## Mode B Playback Rules

Playback order:

```text
Manager Greeting
↓
Manager Dialog

↓

Natnael Greeting
↓
Natnael Dialog

↓

Visitor Greeting
↓
Visitor Dialog
```

Only one file may play at a time.

---

# Common Audio Folder

Purpose:

```text
Shared audio assets.
```

Directory:

```text
audio/common/
```

Examples:

```text
audio/common/

system_ready.wav

error.wav

playback_paused.wav
```

This folder exists for future expansion.

Current V3 implementation may not require files in this folder.

---

# Playback Queue Rules

The Greeting Manager shall produce a queue.

Example:

```text
Manager Greeting
Natnael Greeting
Visitor Greeting
Common Dialog
```

Playback Service processes:

```text
FIFO
(First In First Out)
```

---

# Audio File Requirements

Required format:

```text
WAV
```

Recommended specification:

```text
16-bit PCM

Mono

16 kHz
```

Acceptable:

```text
22.05 kHz

44.1 kHz
```

All audio files should use the same format throughout the project.

---

# Audio Duration Guidelines

Greeting Audio:

```text
2–10 seconds
```

Recommended:

```text
3–5 seconds
```

---

Dialog Audio:

```text
5–60 seconds
```

Recommended:

```text
10–30 seconds
```

---

# Playback Priority Rules

Playback order shall always be:

```text
Priority Queue
↓
Greeting Queue
↓
Dialog Queue
```

Never:

```text
Dialog
↓
Greeting
```

---

# Simultaneous Playback Policy

Forbidden:

```text
Audio A
+
Audio B
```

simultaneously.

Only:

```text
Audio A
↓
Finished
↓
Audio B
```

is allowed.

---

# Dialog Interruption Framework

Purpose:

Future extensibility.

Applies only to:

```text
Dialog Playback
```

---

## Interruptible Audio

Allowed:

```text
Common Dialog

User Dialog
```

---

## Non-Interruptible Audio

Forbidden:

```text
Greeting Audio
```

Greeting audio must always finish.

---

# Pause Workflow

Example:

```text
Dialog Playing
↓
Pause
↓
Store Position
```

---

# Resume Workflow

Example:

```text
Resume
↓
Continue From Stored Position
↓
Finish Playback
```

Dialog must not restart from:

```text
0%
```

---

# Missing Audio Behavior

If audio is missing:

```text
Log Error
```

System shall continue operating.

System must never crash because:

```text
Missing Greeting

Missing Dialog
```

---

# User Audio Mapping Rules

Every enrolled user may contain:

```json
{
    "user_id": "natnael",
    "preferred_language": "amharic"
}
```

Greeting resolution:

```text
audio/amharic/greetings/natnael.wav
```

Dialog resolution:

Mode A:

```text
audio/amharic/dialogs/common_dialog.wav
```

Mode B:

```text
audio/amharic/dialogs/natnael.wav
```

---

# Recommended Audio Inventory

For each language:

## Greetings

```text
manager.wav

natnael.wav

visitor.wav

admin.wav
```

---

## Dialogs

Mode A:

```text
common_dialog.wav
```

Mode B:

```text
manager.wav

natnael.wav

visitor.wav

admin.wav
```

---

# Audio Validation Requirements

The system shall validate:

✅ File exists

✅ File readable

✅ Supported format

✅ Playback successful

Before attempting playback.

---

# Expansion Support

Future versions may add:

```text
Additional Languages

Dynamic Dialogs

Remote Audio Update

Audio Playlists

Event-Based Audio
```

without changing the existing directory structure.

---

# Success Criteria

Audio architecture is successful when:

✅ Single-user greetings work.

✅ Multi-user greetings work.

✅ Priority ordering works.

✅ Mode A works.

✅ Mode B works.

✅ No overlapping audio occurs.

✅ Dialog interruption works.

✅ Missing-file handling works.

✅ Language-based playback works.

✅ Playback service remains the single audio controller.

---

# End of Document
