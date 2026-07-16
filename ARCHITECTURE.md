# Architecture

## Purpose

This document defines the technical architecture of the Offline Multimodal Conversational Robot.

The architecture is designed specifically to achieve:

- A complete working implementation within one working day
- A stable end-to-end demonstration
- Offline operation
- Modular design
- Event-driven workflow
- Simple maintainable implementation

The goal is not perfect architecture.

The goal is a complete working system that can successfully perform the full demonstration workflow.

---

# Architecture Principles

## Principle 1: Demonstration First

Primary Priority:

1. End-to-end functionality
2. Successful demonstration
3. Stability
4. Maintainability
5. Performance

When implementation choices exist, choose the simplest solution that satisfies:

- README.md
- DEMO_SCRIPT.md
- ACCEPTANCE_TESTS.md

Avoid:

- Over-engineering
- Enterprise architecture patterns
- Distributed systems
- Premature optimization
- Unnecessary abstractions

---

## Principle 2: Offline Operation

The robot must operate completely offline.

No cloud services may be used.

The system must not depend on:

- OpenAI API
- Claude API
- ChatGPT API
- Ollama
- Cloud Speech Services
- Text-To-Speech APIs
- RAG Systems
- Vector Databases

All processing occurs locally.

---

## Principle 3: Event Driven Behavior

The robot is event driven.

Components communicate through events.

Events trigger:

- State transitions
- Audio playback
- Recognition actions
- Timeout handling
- Conversation actions

---

## Principle 4: Continuous Operation

The robot continuously processes:

- Webcam input
- Microphone input

The robot remains ready for interaction at all times.

No manual activation is required.

---

# High Level System Architecture

Camera Service
        │
        ▼
Face Detection
        │
        ▼
Face Recognition
        │
        ▼
Event Bus
        │
        ▼
Finite State Machine
        │
        ▼
Conversation Manager

Microphone Service
        │
        ▼
Wake Word Detection
        │
        ▼
Language Selection
        │
        ▼
Whisper
        │
        ▼
Scenario Matching
        │
        ▼
Audio Playback

        │
        ▼

VAD Monitoring

Streamlit Dashboard
        │
        ▼
Monitoring & Administration Only

---

# Layered Architecture

## Presentation Layer

Components:

- Streamlit Dashboard
- Enrollment Page
- Scenario Management Page
- Settings Page

Purpose:

Provide monitoring and administration.

Responsibilities:

- Display webcam feed
- Display logs
- Display current state
- Display recognized users
- Display playback status
- Manage users
- Manage scenarios
- Manage settings

Restrictions:

Must never perform:

- Face recognition
- Whisper transcription
- Scenario matching
- Wake word detection
- VAD processing
- Audio playback control
- FSM transitions

Business logic is prohibited in Streamlit pages.

---

## Service Layer

Components:

- Camera Service
- Audio Service
- Face Recognition Service
- Whisper Service
- VAD Service
- Playback Service
- Conversation Service

Purpose:

Execute application business logic.

Responsibilities:

- Process media streams
- Manage hardware devices
- Recognize users
- Transcribe speech
- Play audio
- Detect interruptions
- Publish events

Services communicate through the Event Bus.

---

## Core Layer

Components:

- Event Bus
- State Machine
- Shared Application State

Purpose:

Coordinate the entire application.

Responsibilities:

- Event routing
- State management
- Workflow orchestration
- Service coordination

The Core Layer controls system behavior.

---

## Persistence Layer

Purpose:

Store application data.

Storage Types:

- Face database
- Dialog database
- Application settings

Storage Format:

- JSON
- Image files
- Audio files

No database server is required.

File-based storage is sufficient.

---

# Project Service Architecture

## Camera Service

File:

utils/camera_service.py

Purpose:

Provide continuous webcam monitoring.

Responsibilities:

- Open webcam
- Read frames
- Deliver frames
- Coordinate face detection
- Coordinate face recognition
- Publish face events

Requirements:

- Webcam opened once
- Webcam remains open
- Continuous processing
- Background thread

Generated Events:

- FACE_DETECTED
- FACE_RECOGNIZED
- FACE_UNKNOWN
- FACE_LOST

---

## Face Recognition Service

File:

utils/face_recognition.py

Purpose:

Recognize enrolled users.

Responsibilities:

- Load user faces
- Generate embeddings
- Compare embeddings
- Calculate confidence scores
- Match users

Requirements:

- Multiple user support
- Persistent storage
- Dlib embeddings

Demonstration accuracy is more important than perfect biometric performance.

---

## Audio Service

File:

utils/audio_service.py

Purpose:

Provide continuous microphone monitoring.

Responsibilities:

- Open microphone
- Capture audio
- Buffer audio
- Deliver audio to Whisper
- Deliver audio to VAD
- Monitor wake words

Requirements:

- Continuous operation
- Background thread
- Microphone initialized once

---

## Whisper Service

File:

utils/whisper_utils.py

Purpose:

Provide speech recognition.

Responsibilities:

- Load Whisper
- Language detection
- Wake word detection
- Speech transcription

Requirements:

- Offline operation
- Cached model
- Singleton model
- Load one time only
- Reuse continuously

Supported Languages:

- English
- Amharic
- Arabic

---

## Scenario Service

Implemented inside:

utils/conversation_manager.py

Purpose:

Match transcribed speech.

Responsibilities:

- Normalize text
- Search scenarios
- Select response audio

Workflow:

Speech

↓

Whisper

↓

Normalize

↓

Scenario Match

↓

Locate Audio

---

## Playback Service

File:

utils/playback.py

Purpose:

Manage prerecorded responses.

Responsibilities:

- Play audio
- Pause audio
- Resume audio
- Restart audio
- Track playback state

Requirements:

- WAV support
- MP3 support
- Playback position tracking

---

## VAD Service

File:

utils/vad_handler.py

Purpose:

Detect interruptions.

Responsibilities:

- Monitor user speech
- Detect interruptions
- Detect silence
- Coordinate playback

Requirements:

- Real-time operation
- Noise tolerance

---

## Conversation Service

File:

utils/conversation_manager.py

Purpose:

Manage conversation workflow.

Responsibilities:

- FSM coordination
- Language context
- Timeout handling
- Event handling
- Scenario matching

This service orchestrates the robot.

---

# Event Bus Architecture

File:

utils/event_bus.py

Purpose:

Provide communication between services.

Responsibilities:

- Publish events
- Subscribe handlers
- Route events
- Dispatch events

Requirements:

- Thread safe
- In-process implementation
- Lightweight

Do not implement:

- Kafka
- RabbitMQ
- Redis Pub/Sub
- External brokers

A simple local event bus is sufficient.

---

# Service Communication Rules

Allowed:

Service
↓
Event Bus
↓
Service

Example:

Camera Service
↓
FACE_RECOGNIZED
↓
Conversation Service

Not Allowed:

Camera Service
↓
Direct Service Call
↓
Conversation Service

All services communicate through events.

This keeps services loosely coupled.

---

# Real-Time Camera Pipeline

Application Startup

↓

Initialize Webcam

↓

Capture Frame

↓

Detect Face

↓

Recognize Face

↓

Publish Event

↓

Update Dashboard State

↓

Repeat Continuously

The camera thread remains active for the application lifetime.

---

# Real-Time Audio Pipeline

Application Startup

↓

Initialize Microphone

↓

Capture Audio

↓

Detect Wake Word

↓

Language Selection

↓

Speech Recognition

↓

Scenario Matching

↓

Audio Playback

↓

Monitor Interruptions

↓

Repeat Continuously

The microphone thread remains active for the application lifetime.

---

# Automatic Greeting Workflow

User Appears

↓

Face Detected

↓

Face Recognized

↓

Publish FACE_RECOGNIZED

↓

Greeting Audio Playback

↓

WAITING_FOR_WAKE_WORD

No user action is required.

Greeting must occur automatically.

---

# Conversation Workflow

Wake Word Detected

↓

Language Selected

↓

Conversation Activated

↓

Capture User Speech

↓

Whisper Transcription

↓

Text Normalization

↓

Scenario Match

↓

Find Audio File

↓

Play Audio

↓

Wait For Next Input

---

# Interruption Workflow

Response Playing

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

↓

Continue Playback

Playback resumes from its previous position.

Playback must not restart.

---

# Thread Model

Required Threads:

1. Camera Thread

2. Audio Thread

3. Playback Thread

4. VAD Thread

5. Conversation Thread

Additional threads should be avoided unless necessary.

Keep concurrency simple.

---

# Failure Isolation

A failure in one service should not terminate the application.

Examples:

Playback Failure

↓

Log Error

↓

Application Continues

Face Recognition Failure

↓

Log Error

↓

Camera Remains Active

VAD Failure

↓

Log Error

↓

Conversation Continues

The application should remain operational whenever possible.

---

# Shared State Management

File:

utils/state_manager.py

Purpose:

Provide shared runtime state.

Examples:

- Current State
- Current Language
- Recognized User
- Playback Status
- Wake Word Status
- Camera Status

Dashboard pages read from shared state.

Business logic does not execute in shared state.

---

# Startup Sequence

Load Configuration

↓

Initialize Logging

↓

Initialize Shared State

↓

Initialize Event Bus

↓

Initialize Camera

↓

Initialize Audio Devices

↓

Load Face Database

↓

Load Whisper Model

↓

Start Service Threads

↓

Initialize FSM

↓

Enter IDLE State

↓

Begin Monitoring

---

# Shutdown Sequence

Stop Service Threads

↓

Stop Playback

↓

Release Webcam

↓

Release Microphone

↓

Persist Required State

↓

Shutdown Logging

↓

Exit Application

---

# Demonstration Readiness Criteria

The architecture is considered successful when the following workflow can be completed:

User Appears

↓

Face Recognized

↓

Greeting Played

↓

Wake Word Detected

↓

Language Selected

↓

Question Asked

↓

Scenario Matched

↓

Response Played

↓

User Interrupts

↓

Playback Paused

↓

Polite Audio Played

↓

Playback Resumes

↓

Conversation Timeout

↓

Return To Idle

If the full workflow succeeds, the architecture satisfies the project objective.