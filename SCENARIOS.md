# Scenario Matching Specification

## Purpose

This document defines how conversations work.

The robot is not an LLM.

The robot never generates responses.

The robot never creates speech.

The robot only selects prerecorded audio files.

The goal is a simple, deterministic, and reliable conversation system that can be implemented within one working day.

---

# Core Rule

Every response must already exist as a prerecorded audio file.

Valid:

User Question
↓
Scenario Match
↓
Play Existing Audio

Invalid:

User Question
↓
Generate New Response
↓
Generate Speech

Generated responses are prohibited.

Generated speech is prohibited.

---

# Conversation Workflow

User Speech

↓

Whisper

↓

Text Transcription

↓

Normalize Text

↓

Scenario Match

↓

Locate Audio File

↓

Play Response Audio

---

# Wake Word Workflow

The robot remains in a listening state.

A wake word activates the conversation.

Workflow:

Waiting For Wake Word

↓

Wake Word Detected

↓

Language Selected

↓

Conversation Activated

↓

User Speaks

---

# Wake Word Storage

Wake words are stored in:

config/settings.json

Example:

{
  "wake_words": {
    "english": [
      "hello robot",
      "hey robot",
      "computer"
    ],
    "amharic": [
      "ሰላም ሮቦት",
      "ሄይ ሮቦት"
    ],
    "arabic": [
      "مرحبا روبوت",
      "أهلا روبوت"
    ]
  }
}

Wake words are never stored in dialog_config.json.

---

# Scenario Storage

Scenario file:

audio/config/dialog_config.json

Structure:

{
  "english": [
    {
      "user_text": "what is your name",
      "response_audio": "name.wav"
    }
  ],

  "amharic": [],

  "arabic": []
}

---

# Scenario Definition

Each scenario contains:

- user_text
- response_audio

Example:

{
  "user_text": "what is your name",
  "response_audio": "audio/english/name.wav"
}

---

# Text Normalization

Before matching:

Convert text to lowercase.

Remove punctuation.

Remove extra spaces.

Trim whitespace.

Example:

Input:

"What is your name?!"

Normalized:

"what is your name"

---

# Matching Strategy

Priority:

1. Exact Match
2. Keyword Match

Highest scoring match wins.

Keep implementation simple.

Demonstration reliability is more important than advanced NLP.

---

# Forbidden Matching Methods

Do NOT use:

- Semantic Search
- Embeddings
- Vector Databases
- LLMs
- GPT
- Claude API
- AI Reasoning

The matching engine must remain deterministic.

---

# Multi-Language Matching

Scenarios are matched only within the active language.

Example:

Language:

English

Question:

What is your name?

Search only English scenarios.

Do not search Amharic or Arabic scenarios.

---

# Fallback Response

If no matching scenario exists:

Play:

unknown_question.wav

Example:

User asks:

"Tell me a joke"

No matching scenario exists.

Response:

unknown_question.wav

---

# Audio Requirements

Supported Formats:

- WAV
- MP3

Recommended:

- WAV

All referenced files must exist.

Missing audio files must be logged.

---

# Scenario Validation

The system must validate:

- Audio file exists
- user_text exists
- response_audio exists
- language exists

Invalid scenarios must be logged.

---

# Demonstration Requirements

The scenario engine is complete when:

✓ Scenario file loads

✓ Scenarios validate successfully

✓ Language filtering works

✓ Text normalization works

✓ Exact matching works

✓ Keyword matching works

✓ Audio response is selected correctly

✓ Fallback response works

The goal is reliable deterministic behavior.