# EthioChatbot V2 Scenario Specification

## Purpose

This document defines how conversations are implemented in EthioChatbot V2.

EthioChatbot V2 uses a deterministic scenario-based conversation engine.

The robot does not generate responses.

The robot does not generate speech.

The robot only:

- Recognizes speech
- Matches scenarios
- Selects prerecorded audio
- Plays prerecorded audio

The objective is to provide reliable multilingual conversations that are lightweight enough to run on Raspberry Pi 4 (8GB).

---

# Design Principles

## Principle 1

Every response must already exist before the application starts.

Valid:

User Question

↓

Scenario Match

↓

Existing Audio File

↓

Playback

Invalid:

User Question

↓

Generate New Response

↓

Generate New Audio

Generated responses are prohibited.

---

## Principle 2

Conversation behavior must be deterministic.

The same question should always produce the same response.

Example:

Question:

What is your name?

Response:

name.wav

Always.

---

## Principle 3

Conversation behavior must be offline.

No internet access is required.

No cloud services are used.

---

## Principle 4

The implementation must remain lightweight enough for Raspberry Pi deployment.

Avoid:

- LLMs
- Semantic Search
- Embeddings
- Vector Databases
- Large NLP Frameworks

---

# Conversation Architecture

Workflow:

Wake Word

↓

Conversation Active

↓

User Speaks

↓

Whisper

↓

Transcription

↓

Normalize Text

↓

Scenario Match

↓

Select Audio

↓

Playback

↓

Wait For Next Question

↓

Timeout

↓

WAITING_FOR_WAKE_WORD

---

# Conversation Language

EthioChatbot V2 supports:

- English
- Amharic
- Arabic

Each conversation operates within exactly one active language.

Store:

current_language

Example:

English

↓

Only English scenarios searched

Amharic

↓

Only Amharic scenarios searched

Arabic

↓

Only Arabic scenarios searched

---

# Language Selection Model

EthioChatbot V2 does not use a dedicated language selection phase.

Language is determined automatically.

Priority:

1. Wake Word Language
2. User Preferred Language
3. English

---

## English Example

Wake Word:

Hello Robot

↓

current_language = english

---

## Amharic Example

Wake Word:

ሰላም ሮቦት

↓

current_language = amharic

---

## Arabic Example

Wake Word:

مرحبا روبوت

↓

current_language = arabic

---

# Scenario Storage

File:

audio/config/dialog_config.json

Purpose:

Store all conversation definitions.

---

# Scenario File Structure

Example:

{
  "english": [
    {
      "user_text": "what is your name",
      "response_audio": "audio/english/name.wav"
    },
    {
      "user_text": "goodbye",
      "response_audio": "audio/english/goodbye.wav"
    }
  ],

  "amharic": [
    {
      "user_text": "ስምህ ማን ነው",
      "response_audio": "audio/amharic/name.wav"
    }
  ],

  "arabic": [
    {
      "user_text": "ما اسمك",
      "response_audio": "audio/arabic/name.wav"
    }
  ]
}

---

# Scenario Definition

Each scenario contains:

user_text

response_audio

Example:

{
  "user_text": "what is your name",
  "response_audio": "audio/english/name.wav"
}

Meaning:

When the user asks:

what is your name

Play:

audio/english/name.wav

---

# Text Normalization

All transcriptions must be normalized before matching.

Required Steps:

1. Convert to lowercase
2. Remove punctuation
3. Remove duplicate spaces
4. Trim whitespace

---

## Example

Input:

"What is your name?!"

↓

Normalized:

"what is your name"

---

# Matching Strategy

Priority Order:

1. Exact Match
2. Keyword Match
3. Fallback Response

Keep implementation simple.

Demonstration reliability is more important than advanced NLP.

---

# Exact Matching

Example:

Scenario:

what is your name

User Input:

what is your name

Result:

Match Success

This is the preferred method.

---

# Keyword Matching

Example:

Scenario:

what is your name

User Input:

hello can you tell me what is your name

Result:

Keyword Match

Used when exact match fails.

---

# Unsupported Matching Methods

The following are prohibited:

- Semantic Search
- Embedding Search
- Vector Databases
- LLM Reasoning
- GPT Search
- Claude API
- Text Generation

The robot remains deterministic.

---

# Scenario Cache

Scenarios should load once during startup.

Recommended:

dialog_config.json

↓

Load

↓

Validate

↓

Create Dictionaries

↓

Memory Cache

Example:

english_lookup

amharic_lookup

arabic_lookup

Use cached lookups during runtime.

Avoid repeated JSON reads.

---

# Multi-Language Matching

Only search scenarios belonging to the active language.

Example:

current_language = english

Search:

english_lookup

Do Not Search:

amharic_lookup

arabic_lookup

This reduces CPU usage.

---

# Fallback Response

When no scenario matches:

Play:

unknown_question.wav

Example:

User:

Tell me a joke

↓

No Matching Scenario

↓

unknown_question.wav

---

# Audio Storage Rules

English Audio:

audio/english/

Amharic Audio:

audio/amharic/

Arabic Audio:

audio/arabic/

---

# Supported Audio Formats

Supported:

- WAV
- MP3

Recommended:

WAV

Reason:

- Faster loading
- Simpler playback
- Better Raspberry Pi performance

---

# Audio Validation

Before startup:

Validate:

- Audio file exists
- Audio path is valid
- Scenario is complete

Invalid entries must be logged.

---

# Personalized Greeting Audio

Greeting files are independent from scenarios.

Examples:

audio/english/greetings/

manager.wav

natnael.wav

visitor.wav

Fallback:

greeting.wav

Greeting selection is based on recognized user identity.

---

# Preferred Language Metadata

Each enrolled user may contain:

{
  "user_id": "natnael",
  "priority": 2,
  "preferred_language": "amharic"
}

Purpose:

Language determination fallback.

Priority:

Wake Word Language

↓

Preferred Language

↓

English

---

# Conversation Context Rules

Conversation context remains active until timeout.

Store:

current_language

Example:

Wake Word:

ሰላም ሮቦት

↓

current_language = amharic

↓

Question 1

↓

Question 2

↓

Question 3

↓

Timeout

Language remains unchanged.

---

# Timeout Behavior

Conversation Timeout:

30 seconds

Recommended.

Workflow:

No User Activity

↓

TIMEOUT

↓

Clear Context

↓

WAITING_FOR_WAKE_WORD

Do not return directly to IDLE if faces remain visible.

---

# Face Persistence Relationship

Face visibility controls session availability.

Users Visible

↓

WAITING_FOR_WAKE_WORD

↓

Conversation

↓

Timeout

↓

WAITING_FOR_WAKE_WORD

Users Still Visible

↓

Remain Available

---

Users Gone

↓

RETURN_TO_IDLE

↓

IDLE

---

# Raspberry Pi Optimization Rules

Minimize memory usage.

Recommended:

- Scenario cache
- Dictionary lookups
- Lightweight matching

Avoid:

- Runtime AI inference beyond Whisper
- Semantic indexing
- Large language models

---

# Scenario Validation Rules

A valid scenario must contain:

✓ user_text

✓ response_audio

✓ existing audio file

✓ valid language section

A scenario is invalid if:

✗ Missing audio

✗ Missing text

✗ Invalid path

---

# Demonstration Examples

## English

Wake Word:

Hello Robot

↓

Question:

What is your name

↓

Response:

audio/english/name.wav

---

## Amharic

Wake Word:

ሰላም ሮቦት

↓

Question:

ስምህ ማን ነው

↓

Response:

audio/amharic/name.wav

---

## Arabic

Wake Word:

مرحبا روبوت

↓

Question:

ما اسمك

↓

Response:

audio/arabic/name.wav

---

# Demonstration Success Criteria

The Scenario Engine is complete when:

✓ English scenarios load

✓ Amharic scenarios load

✓ Arabic scenarios load

✓ Scenario validation works

✓ Text normalization works

✓ Exact matching works

✓ Keyword matching works

✓ Cached lookups work

✓ Fallback response works

✓ Correct audio is selected

✓ Raspberry Pi performance remains acceptable

✓ End-to-end multilingual conversations succeed

The Scenario Engine is the authoritative conversation behavior specification for EthioChatbot V2.
