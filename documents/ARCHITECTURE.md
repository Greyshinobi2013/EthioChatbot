# EthioChatbot V2 Architecture

## Purpose

This document defines the technical architecture of EthioChatbot V2.

The architecture is designed specifically for:

- Fully offline operation
- Raspberry Pi 4 (8GB RAM) deployment
- Multilingual support
- Multi-face recognition
- Deterministic conversations
- Event-driven processing
- Finite State Machine control
- Completion within 5 hours of implementation effort
- End-to-end demonstration readiness

The architecture prioritizes:

1. End-to-end workflow completion
2. Stability
3. Simplicity
4. Raspberry Pi compatibility
5. Maintainability

The architecture does not prioritize production-scale optimization.

---

# Architecture Principles

## Principle 1: Offline First

All processing must occur locally.

No cloud services are allowed.

Prohibited:

- OpenAI API
- Claude API
- ChatGPT API
- Gemini API
- Azure OpenAI
- Ollama
- RAG
- Vector Databases
- External AI Services

Permitted:

- Local Whisper
- Local Face Recognition
- Local Scenario Matching
- Local Audio Playback

---

## Principle 2: Deterministic Conversation

The robot never generates responses.

Every response must already exist as a prerecorded audio file.

Conversation Flow:

Speech

↓

Whisper

↓

Transcription

↓

Scenario Match

↓

Audio Selection

↓

Playback

No response generation is allowed.

---

## Principle 3: Demonstration First

This project is intended to be demonstratable within five hours of development effort.

Choose:

- Simpler solutions
- Stable solutions
- Easy-to-debug solutions

Avoid:

- Distributed architectures
- Enterprise frameworks
- Excessive abstraction
- Premature optimization

---

## Principle 4: Event Driven Processing

The robot reacts to events.

Examples:

- FACE_RECOGNIZED
- WAKE_WORD_DETECTED
- SCENARIO_MATCHED
- INTERRUPTION_DETECTED
- TIMEOUT_OCCURRED

Events drive behavior.

---

## Principle 5: State Machine Control

The robot is controlled by a finite state machine.

The FSM manages:

- Greetings
- Wake word waiting
- Active conversations
- Interruptions
- Timeouts
- Return to idle

---

# System Architecture

EthioChatbot V2 consists of four layers:

Presentation Layer

↓

Service Layer

↓

Core Layer

↓

Persistence Layer

---

# Presentation Layer

Purpose:

Monitoring and administration.

Components:

- Dashboard
- Face Enrollment
- Scenario Management
- Settings

Implementation:

Streamlit

Files:

pages/1_Dashboard.py

pages/2_Enroll_Face.py

pages/3_Manage_Scenarios.py

pages/4_Settings.py

Responsibilities:

- Display camera feed
- Display logs
- Display recognized users
- Display conversation state
- Manage settings
- Manage scenarios

Restrictions:

Presentation Layer must never perform:

- Face Recognition
- Whisper STT
- Scenario Matching
- State Transitions
- Playback Handling

Business logic is prohibited in Streamlit pages.

---

# Service Layer

Purpose:

Execute all robot functionality.

Services:

- Camera Service
- Audio Service
- Face Recognition Service
- Whisper Service
- VAD Service
- Playback Service
- Conversation Service

All services run continuously.

All services communicate through the Event Bus.

---

# Core Layer

Purpose:

Coordinate robot behavior.

Components:

- Event Bus
- Finite State Machine
- Shared State Manager

Responsibilities:

- Event Routing
- State Transitions
- Workflow Coordination
- System State Management

---

# Persistence Layer

Purpose:

Store robot data.

Storage:

- Faces
- Face Metadata
- Dialog Scenarios
- Audio Assets
- Settings

Format:

- JSON
- Image Files
- Audio Files

No database server is required.

---

# Service Architecture

## Camera Service

File:

utils/camera_service.py

Purpose:

Continuous camera monitoring.

Responsibilities:

- Open webcam
- Capture frames
- Resize frames
- Provide frames to recognition pipeline
- Track visible users

Runtime:

Continuous

Thread:

Camera Thread

Generated Events:

- FACE_DETECTED
- FACE_RECOGNIZED
- FACE_LOST

---

## Face Recognition Service

File:

utils/face_recognition.py

Purpose:

Identify enrolled users.

Responsibilities:

- Load embeddings
- Compare embeddings
- Calculate confidence
- Determine user identity

Optimization:

Embeddings loaded once.

Embeddings reused.

Recommended:

Recognition every 10 frames.

Detection every frame.

---

## Audio Service

File:

utils/audio_service.py

Purpose:

Continuous microphone monitoring.

Responsibilities:

- Capture microphone audio
- Buffer audio
- Forward audio to Whisper
- Forward audio to VAD

Runtime:

Continuous

Thread:

Audio Thread

---

## Whisper Service

File:

utils/whisper_utils.py

Purpose:

Speech recognition.

Responsibilities:

- Wake word detection
- Speech transcription
- Language recognition

Requirements:

- Offline only
- Loaded once
- Reused continuously

Recommended Model:

base

Optimization Target:

Raspberry Pi 4 (8GB)

---

## VAD Service

File:

utils/vad_handler.py

Purpose:

Detect speech interruptions.

Responsibilities:

- Detect speech activity
- Detect silence
- Trigger interruption events

Generated Events:

- INTERRUPTION_DETECTED
- INTERRUPTION_CLEARED

---

## Playback Service

File:

utils/playback.py

Purpose:

Manage prerecorded audio.

Responsibilities:

- Play audio
- Pause audio
- Resume audio
- Restart audio
- Track playback position

Requirements:

- WAV support
- MP3 support
- Resume support

Thread:

Playback Thread

---

## Conversation Service

File:

utils/conversation_manager.py

Purpose:

Manage conversation workflow.

Responsibilities:

- Greeting logic
- Language context
- Scenario matching
- Timeout handling
- State transitions

This service orchestrates conversation behavior.

---

# Event Bus

File:

utils/event_bus.py

Purpose:

Service communication.

Responsibilities:

- Publish events
- Subscribe handlers
- Route events
- Dispatch callbacks

Requirements:

- Lightweight
- Thread-safe
- Local process only

No external messaging systems.

---

# State Manager

File:

utils/state_manager.py

Purpose:

Runtime state storage.

Stores:

- Current State
- Current Language
- Active Users
- Camera Status
- Playback Status
- Wake Word Status

Shared state must be lightweight.

---

# Multi-Face Architecture

The robot supports multiple simultaneous users.

Workflow:

Faces Detected

↓

Recognize Users

↓

Load Priorities

↓

Sort By Priority

↓

Sequential Greeting

Example:

Priority 1

↓

Priority 2

↓

Priority 3

---

# User Metadata Model

Stored during enrollment.

Example:

{
    "user_id": "natnael",
    "priority": 2,
    "preferred_language": "amharic"
}

Stored Fields:

- user_id
- priority
- preferred_language
- embedding_path
- image_path

---

# Greeting Architecture

Greeting Language:

English

Always.

Workflow:

Recognize Users

↓

Priority Sort

↓

Greeting User 1

↓

Greeting User 2

↓

Greeting User 3

↓

WAITING_FOR_WAKE_WORD

No language switching before greetings.

---

# Wake Word Architecture

Wake words determine session language.

Examples:

English:

Hello Robot

↓

English Session

Amharic:

ሰላም ሮቦት

↓

Amharic Session

Arabic:

مرحبا روبوت

↓

Arabic Session

No separate Language Selection state exists.

---

# Language Context Architecture

Language priority:

1. Wake Word Language
2. User Preferred Language
3. English

Store:

current_language

After activation:

All STT

All Scenarios

All Responses

use current_language.

---

# Face Persistence Architecture

Each active user stores:

last_seen timestamp

Example:

{
    "user_id": "natnael",
    "last_seen": 123456789
}

Updated continuously.

---

# Face Lost Detection Architecture

Recommended:

5 second timeout

Workflow:

User Visible

↓

User Leaves Camera

↓

5 Seconds Pass

↓

FACE_LOST

If active users remain:

WAITING_FOR_WAKE_WORD

If no users remain:

RETURN_TO_IDLE

↓

IDLE

---

# Conversation Architecture

WAITING_FOR_WAKE_WORD

↓

Wake Word

↓

CONVERSATION_ACTIVE

↓

Speech

↓

Whisper

↓

Scenario Match

↓

Audio Playback

↓

More Speech

↓

Continue Conversation

↓

Timeout

↓

WAITING_FOR_WAKE_WORD

---

# Scenario Matching Architecture

Conversation is deterministic.

Workflow:

Speech

↓

Whisper

↓

Normalize

↓

Scenario Match

↓

Audio File

↓

Playback

No AI reasoning.

No semantic search.

No vector database.

---

# Interruption Architecture

Workflow:

Playing Audio

↓

User Speaks

↓

VAD Detects Speech

↓

Pause Playback

↓

Play please_wait.wav

↓

Wait For Silence

↓

Resume Original Audio

Playback resumes from the exact position.

Playback does not restart.

---

# Raspberry Pi 4 Optimization Profile

Target Hardware:

- Raspberry Pi 4
- 8 GB RAM
- 32 GB Storage
- 1.8 GHz CPU

---

## Camera Optimization

Resolution:

640 x 480

Benefits:

- Lower CPU usage
- Lower memory usage
- Faster detection

---

## Recognition Optimization

Detect:

Every frame

Recognize:

Every 10th frame

Benefits:

- Reduced CPU load
- Faster response

---

## Whisper Optimization

Recommended:

base model

Benefits:

- English
- Amharic
- Arabic

while remaining deployable on Pi 4.

---

## Embedding Cache

Load once:

Faces

↓

Embeddings

↓

Memory Cache

No repeated generation.

---

## Scenario Cache

Load on startup.

Create:

english_lookup

amharic_lookup

arabic_lookup

Use dictionary lookup during runtime.

---

## Memory Policy

Keep:

- latest_frame
- latest_audio_chunk

Avoid:

- frame history
- audio history
- duplicate frame storage

---

# Thread Architecture

Required Threads:

1. Camera Thread

2. Audio Thread

3. Playback Thread

4. VAD Thread

5. Conversation Thread

Only required threads should exist.

Keep concurrency simple.

---

# Startup Sequence

Load Configuration

↓

Initialize Logging

↓

Initialize Event Bus

↓

Initialize State Manager

↓

Load Face Database

↓

Load Face Embeddings

↓

Load Whisper

↓

Initialize Camera

↓

Initialize Audio Devices

↓

Start Service Threads

↓

Initialize FSM

↓

Enter IDLE

---

# Shutdown Sequence

Stop Threads

↓

Stop Playback

↓

Release Camera

↓

Release Audio

↓

Save State

↓

Shutdown Logging

↓

Exit

---

# Architecture Success Criteria

The architecture is considered successful when:

✓ Multiple users can be recognized

✓ Users can be prioritized

✓ Greetings occur sequentially

✓ Wake words determine conversation language

✓ English works

✓ Amharic works

✓ Arabic works

✓ Scenarios match correctly

✓ Responses play correctly

✓ Interruptions pause playback

✓ Playback resumes correctly

✓ Faces persist across conversations

✓ FACE_LOST works

✓ WAITING_FOR_WAKE_WORD persists while users remain visible

✓ IDLE activates when all users leave

✓ The entire workflow runs on Raspberry Pi 4 (8GB)

✓ The full demonstration succeeds end-to-end
