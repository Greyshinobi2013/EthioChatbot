# ROLE

You are a Principal Software Architect, Robotics Engineer, Computer Vision Engineer, Speech Processing Engineer, and Senior Python Developer.

Your task is to design and implement a complete Offline Multimodal Conversational Robot similar to Emo Robot.

The objective is to deliver a complete working demonstration within one working day.

This project prioritizes:

1. End-to-end functionality
2. Integration between modules
3. Demonstration stability
4. Maintainability
5. Performance

The goal is not to build a perfect production platform.

The goal is to build a reliable, demonstratable offline conversational robot.

---

# PROJECT NAME

Offline Multimodal Conversational Robot

---

# DEMONSTRATION FIRST PRINCIPLE

This project must be completed within one working day.

When implementation choices exist:

Choose the simplest solution that:

- Satisfies acceptance tests
- Satisfies the demonstration workflow
- Preserves offline operation
- Preserves modularity

Avoid:

- Over-engineering
- Premature optimization
- Complex design patterns
- Distributed architectures
- Unnecessary abstractions

A working demonstration is more important than architectural sophistication.

---

# PROJECT OBJECTIVE

Build a robot capable of:

- Face enrollment
- Face detection
- Face recognition
- Automatic greeting
- Wake word detection
- Language selection
- Whisper speech recognition
- Scenario matching
- Audio playback
- Voice activity detection
- Playback interruption handling
- Playback resume
- Conversation timeout
- Return to idle state

All processing must occur locally.

No cloud services may be used.

---

# SUPPORTED LANGUAGES

Required:

- English
- Amharic (አማርኛ)
- Arabic (العربية)

The architecture must support future language expansion.

---

# NON-GOALS

The system does NOT include:

- ChatGPT
- GPT Models
- Claude API
- OpenAI API
- Ollama
- RAG
- Vector Databases
- Text Generation
- LLM Inference
- Semantic Search
- Text-To-Speech
- Cloud Services

---

# CONVERSATION MODEL

This is NOT an LLM chatbot.

The robot never generates responses.

The robot never generates speech.

The robot never creates dynamic conversations.

Every response must already exist as a prerecorded audio file.

Conversation Flow:

User Speech

↓

Whisper Transcription

↓

Text Normalization

↓

Scenario Matching

↓

Locate Audio File

↓

Play Audio

---

# REAL-TIME OPERATION REQUIREMENTS

The robot operates continuously.

At startup:

- Webcam monitoring begins
- Microphone monitoring begins
- Face recognition begins
- Wake word detection begins

No button press is required.

The robot remains ready for interaction at all times.

---

# HIGH LEVEL WORKFLOW

Face Enrollment

↓

Face Detection

↓

Face Recognition

↓

Greeting

↓

Waiting For Wake Word

↓

Wake Word Detection

↓

Language Selection

↓

Conversation Activated

↓

Speech To Text

↓

Scenario Matching

↓

Audio Playback

↓

Interruption Detection

↓

Pause Playback

↓

Play Interruption Audio

↓

Resume Playback

↓

Continue Conversation

↓

Conversation Timeout

↓

Return To Idle

---

# PROJECT STRUCTURE

project/

├── app.py

├── README.md

├── requirements.txt

│
├── faces/

│
├── audio/
│   ├── english/
│   ├── amharic/
│   ├── arabic/
│   └── config/
│       └── dialog_config.json

│
├── config/
│   └── settings.json

│
├── pages/
│   ├── 1_Dashboard.py
│   ├── 2_Enroll_Face.py
│   ├── 3_Manage_Scenarios.py
│   └── 4_Settings.py

│
├── utils/
│   ├── camera_service.py
│   ├── audio_service.py
│   ├── event_bus.py
│   ├── face_recognition.py
│   ├── whisper_utils.py
│   ├── vad_handler.py
│   ├── playback.py
│   ├── conversation_manager.py
│   ├── state_manager.py
│   └── logger.py

│
├── models/

│
└── tests/

---

# TECHNOLOGY STACK

Frontend

- Streamlit

Computer Vision

- OpenCV
- Dlib
- NumPy

Speech Recognition

- OpenAI Whisper

Voice Activity Detection

- WebRTC VAD
- sounddevice

Audio Playback

- pygame

Utilities

- pathlib
- logging
- threading
- json

Programming Language

- Python 3.11+

Only approved technologies may be used.

---

# STREAMLIT RESPONSIBILITIES

Streamlit is not the robot.

Streamlit is only:

- Monitoring dashboard
- Administration interface
- Configuration interface

Streamlit may:

- Display camera feed
- Display logs
- Display system state
- Display users
- Manage scenarios
- Manage settings

Streamlit must never:

- Execute Whisper
- Perform face recognition
- Execute VAD
- Execute playback logic
- Execute scenario matching
- Manage FSM transitions

Business logic belongs exclusively to service modules.

---

# DASHBOARD REQUIREMENTS

File:

pages/1_Dashboard.py

Purpose:

Runtime monitoring.

Features:

## Webcam Feed

Display:

- Live webcam feed
- Face bounding boxes
- Recognized users

## Status Cards

Display:

- System Status
- Recognized User
- Current Language
- Wake Word Status
- VAD Status
- Playback Status
- Conversation State

## System Logs

Display:

- Face detected
- Face recognized
- Greeting played
- Wake word detected
- Language selected
- Conversation activated
- Scenario matched
- Audio played
- Audio paused
- Audio resumed
- Timeout reached

---

# FACE ENROLLMENT REQUIREMENTS

File:

pages/2_Enroll_Face.py

Features:

- Webcam capture
- Image upload
- User ID input
- Save images to faces/
- Enrollment validation
- Display enrolled users

---

# SCENARIO MANAGEMENT REQUIREMENTS

File:

pages/3_Manage_Scenarios.py

Purpose:

Conversation Authoring Tool

Features:

## Wake Word Management

Add wake words

Edit wake words

Delete wake words

## Dialog Management

Each dialog contains:

{
    "user_text": "",
    "response_audio": ""
}

Functions:

- Add dialog
- Edit dialog
- Delete dialog
- Upload audio
- Replace audio
- Preview audio

---

# WAKE WORD STORAGE

Store wake words in:

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

Wake words are not stored in dialog_config.json.

---

# SCENARIO STORAGE

Store dialogs in:

audio/config/dialog_config.json

Example:

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

Only dialog definitions belong here.

---

# SETTINGS REQUIREMENTS

File:

pages/4_Settings.py

Features:

- Face Recognition Sensitivity
- VAD Aggressiveness
- Whisper Model Selection
- GPU Acceleration
- CPU Information
- RAM Information
- GPU Information

Store settings in:

config/settings.json

---

# CORE SERVICES

## Camera Service

File:

utils/camera_service.py

Responsibilities:

- Webcam initialization
- Continuous frame capture
- Face event publication

---

## Audio Service

File:

utils/audio_service.py

Responsibilities:

- Continuous microphone capture
- Wake word monitoring
- Whisper coordination
- VAD coordination

---

## Event Bus

File:

utils/event_bus.py

Responsibilities:

- Publish events
- Subscribe handlers
- Route events
- Thread-safe communication

All services communicate through events.

---

# FACE RECOGNITION MODULE

File:

utils/face_recognition.py

Functions:

load_faces()

detect_face()

match_face()

Requirements:

- Dlib facial embeddings
- Multiple user support
- Persistent storage
- Confidence scoring
- Bounding box output

Demonstration reliability is more important than biometric perfection.

---

# WHISPER MODULE

File:

utils/whisper_utils.py

Functions:

load_model()

transcribe_audio()

detect_wake_word()

Requirements:

- Offline execution
- Model caching
- Singleton loading
- Language detection
- Load once
- Reuse throughout runtime

Supported Models:

- tiny
- base
- small
- medium
- large

Default:

medium

---

# VOICE ACTIVITY DETECTION

File:

utils/vad_handler.py

Functions:

start_vad()

is_speech()

monitor_interruptions()

Requirements:

- Real-time monitoring
- Interruption detection
- Playback coordination
- Noise tolerance

---

# AUDIO PLAYBACK

File:

utils/playback.py

Functions:

play_audio()

pause_audio()

resume_audio()

restart_audio()

notify_user()

Requirements:

- WAV support
- MP3 support
- Playback state tracking
- Playback position tracking

---

# INTERRUPTION BEHAVIOR

Response Audio Playing

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

Resume Original Playback

↓

Continue Conversation

Playback must resume from the exact paused position.

No synthesized speech may be used.

---

# CONVERSATION MANAGER

File:

utils/conversation_manager.py

Responsibilities:

- State transitions
- Wake word activation
- Language context
- Scenario matching
- Timeout handling
- Playback coordination

The conversation manager controls the FSM.

---

# EVENT DRIVEN REQUIREMENTS

The system must use an internal Event Bus.

All workflows are event driven.

Examples:

FACE_RECOGNIZED

WAKE_WORD_DETECTED

SCENARIO_MATCHED

PLAYBACK_STARTED

INTERRUPTION_DETECTED

TIMEOUT_OCCURRED

Direct service-to-service calls should be avoided.

---

# STATE MACHINE REQUIREMENTS

The robot must use a Finite State Machine.

Required States:

IDLE

FACE_ENROLLMENT

FACE_DETECTED

FACE_RECOGNIZED

GREETING

WAITING_FOR_WAKE_WORD

LANGUAGE_SELECTION

CONVERSATION_ACTIVE

PLAYING_AUDIO

INTERRUPTED

TIMEOUT

RETURN_TO_IDLE

All transitions must be logged.

---

# LOGGING REQUIREMENTS

Log:

- Startup
- Shutdown
- Camera initialization
- Model loading
- Enrollment
- Recognition
- Wake words
- Transcription
- Scenario matching
- Audio playback
- Interruptions
- Timeouts
- State transitions
- Errors
- Warnings

---

# TESTING REQUIREMENTS

Unit Tests

- Scenario Matching
- Text Normalization
- FSM Transitions

Integration Tests

- End-to-End Workflow

Manual Demonstration Tests

- Face recognition
- Greeting
- Wake word
- Conversation activation
- Scenario matching
- Playback
- Interruption
- Resume
- Timeout

---

# DEPLOYMENT REQUIREMENTS

Local deployment only.

Application must:

- Start successfully
- Load all models
- Open webcam
- Open microphone
- Initialize services
- Enter IDLE state

No cloud dependencies allowed.

---

# DEFINITION OF DONE

The project is complete only when:

✓ Application starts

✓ Webcam opens

✓ Microphone opens

✓ Face enrollment works

✓ Face recognition works

✓ Greeting audio plays

✓ Wake word detection works

✓ Language selection works

✓ Whisper transcription works

✓ Scenario matching works

✓ Correct audio response plays

✓ VAD interruption detection works

✓ Playback pauses

✓ Interruption audio plays

✓ Playback resumes

✓ Timeout works

✓ Return to idle works

✓ Dashboard works

✓ Scenario management works

✓ Settings page works

✓ End-to-end demonstration succeeds

The final output must be a complete runnable offline conversational robot.