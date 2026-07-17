# EthioChatbot V2

## PROJECT OVERVIEW

EthioChatbot V2 is a fully offline, multilingual, multimodal conversational robot designed for deployment on resource-constrained edge devices such as Raspberry Pi 4 (8GB RAM).

The robot combines:

- Computer Vision
- Face Recognition
- Speech Recognition
- Voice Activity Detection
- Event Driven Architecture
- Finite State Machine Control
- Scenario Based Conversations

The robot does not use any Large Language Models.

The robot never generates responses.

The robot never generates speech.

All conversational outputs are prerecorded audio files.

The primary goal of EthioChatbot V2 is to provide a reliable end-to-end conversational experience using deterministic logic and prerecorded responses.

---

# PROJECT OBJECTIVE

Build a fully offline conversational robot capable of:

- Face Enrollment
- Multi-Face Detection
- Face Recognition
- Priority Based User Recognition
- Personalized Greeting
- Wake Word Detection
- Multilingual Conversation
- Speech To Text
- Scenario Matching
- Audio Playback
- Voice Activity Detection
- Playback Interruption Handling
- Playback Resume
- Face Persistence Tracking
- Conversation Timeout Handling
- Automatic Return To Waiting Mode
- Return To Idle State

The entire workflow must operate locally without internet access.

---

# DEMONSTRATION FIRST PRINCIPLE

This project must be implementable within five hours and fully demonstratable.

Priority Order:

1. End-to-end functionality
2. Stability
3. Integration
4. Maintainability
5. Performance

When implementation choices exist:

Choose the simplest solution that:

- Satisfies acceptance tests
- Supports demonstration
- Preserves offline operation

Avoid:

- Premature optimization
- Complex architectures
- Distributed systems
- Overengineering

---

# DEPLOYMENT TARGET

Primary Target:

Raspberry Pi 4

Specifications:

- 8 GB RAM
- 32 GB Storage
- 1.8 GHz CPU

The system must be optimized for constrained hardware.

---

# PROJECT PHILOSOPHY

The robot is:

- Offline
- Event Driven
- State Machine Based
- Scenario Based
- Deterministic
- Multilingual

The robot is not:

- ChatGPT
- Claude Chatbot
- GPT
- Ollama
- RAG
- Vector Search
- Generative AI
- Text Generator
- TTS System

---

# SUPPORTED LANGUAGES

Required:

- English
- Amharic (አማርኛ)
- Arabic (العربية)

Future language expansion must be possible without architectural changes.

---

# CONVERSATION MODEL

EthioChatbot V2 does not generate conversations.

Conversation Flow:

User Speech

↓

Whisper

↓

Transcription

↓

Text Normalization

↓

Scenario Match

↓

Locate Audio File

↓

Play Audio

Every response must come from an existing prerecorded audio file.

---

# MULTI-FACE RECOGNITION

The robot must support detection of multiple enrolled users simultaneously.

Example:

Detected Users:

- Manager
- Natnael
- Visitor

The robot recognizes all enrolled users visible in the camera frame.

---

# USER PRIORITY SYSTEM

Each enrolled user must contain:

- User ID
- Priority
- Preferred Language

Example:

{
    "user_id": "manager",
    "priority": 1,
    "preferred_language": "english"
}

Lower numbers indicate higher priority.

Recognition order:

Priority 1

↓

Priority 2

↓

Priority 3

---

# GREETING WORKFLOW

When one or more enrolled users are detected:

Recognize Faces

↓

Sort Users By Priority

↓

Play Greetings Sequentially

Example:

Hello Manager.

↓

Hello Natnael.

↓

Hello Visitor.

All greetings use English.

No language selection occurs before greeting.

---

# DEFAULT GREETING LANGUAGE

The greeting language is always:

English

Greeting audio files:

audio/english/greetings/

Examples:

manager.wav

natnael.wav

visitor.wav

Fallback:

greeting.wav

---

# FACE PERSISTENCE

Each recognized user must maintain:

last_seen timestamp

Example:

{
    "user_id": "natnael",
    "last_seen": 1712345678
}

Whenever the user is visible:

last_seen is updated.

---

# FACE LOST DETECTION

Recommended Configuration:

5 seconds

Workflow:

Face Present

↓

Face Disappears

↓

5 Seconds Pass

↓

FACE_LOST Event

If at least one recognized face remains visible:

Remain in WAITING_FOR_WAKE_WORD

If no recognized faces remain:

RETURN_TO_IDLE

↓

IDLE

---

# HIGH LEVEL WORKFLOW

Application Startup

↓

Face Detection

↓

Face Recognition

↓

Priority Sorting

↓

Sequential Greeting

↓

WAITING_FOR_WAKE_WORD

↓

Wake Word Detection

↓

Conversation Active

↓

Speech To Text

↓

Scenario Matching

↓

Audio Playback

↓

Interruptions

↓

Resume Playback

↓

Conversation Timeout

↓

WAITING_FOR_WAKE_WORD

↓

Faces Present?

↓

YES

↓

WAITING_FOR_WAKE_WORD

↓

NO

↓

RETURN_TO_IDLE

↓

IDLE

---

# WAKE WORD SYSTEM

Wake words determine conversation language.

There is no separate language selection stage.

---

## English Wake Words

Examples:

- Hello Robot
- Hey Robot
- Computer

Result:

English Session

---

## Amharic Wake Words

Examples:

- ሰላም ሮቦት
- ሄይ ሮቦት

Result:

Amharic Session

---

## Arabic Wake Words

Examples:

- مرحبا روبوت
- أهلا روبوت

Result:

Arabic Session

---

# LANGUAGE SELECTION RULE

Language selection priority:

1. Wake Word Language
2. User Preferred Language
3. English Fallback

Example:

Preferred Language:

Amharic

User says:

ሰላም ሮቦት

Conversation language:

Amharic

---

# CONVERSATION CONTEXT

Once established:

current_language

remains active during the entire conversation.

Example:

English Session

↓

Question 1

↓

Question 2

↓

Question 3

↓

Timeout

Language context is retained until timeout.

---

# CONVERSATION TIMEOUT

Recommended:

30 seconds

Workflow:

No User Activity

↓

30 Seconds

↓

TIMEOUT

↓

WAITING_FOR_WAKE_WORD

Do not return to IDLE while recognized users remain present.

---

# RETURN TO IDLE

The robot returns to IDLE only when:

No recognized users remain visible.

Workflow:

All Users Lost

↓

RETURN_TO_IDLE

↓

IDLE

---

# PROJECT STRUCTURE

project/

├── app.py

├── README.md

├── requirements.txt

├── faces/

├── audio/

│   ├── english/

│   ├── amharic/

│   ├── arabic/

│   └── config/

│       └── dialog_config.json

├── config/

│   └── settings.json

├── models/

├── pages/

│   ├── 1_Dashboard.py

│   ├── 2_Enroll_Face.py

│   ├── 3_Manage_Scenarios.py

│   └── 4_Settings.py

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

Audio

- pygame

Utilities

- pathlib
- json
- logging
- threading

Language

- Python 3.11+

---

# RASPBERRY PI OPTIMIZATION REQUIREMENTS

## Whisper

Use:

base model

Default:

{
    "whisper_model": "base"
}

---

## Camera Resolution

Recommended:

640 x 480

Do not use:

1920 x 1080

unless explicitly required.

---

## Recognition Frequency

Recommended:

Recognition every 10 frames.

Workflow:

Detect Every Frame

Recognize Every 10 Frames

---

## Face Embedding Cache

Load embeddings once during startup.

Do not regenerate embeddings repeatedly.

---

## Scenario Cache

Load all scenarios at startup.

Build language-level lookup dictionaries.

Example:

english_lookup

amharic_lookup

arabic_lookup

---

## Memory Policy

Keep only:

latest_frame

latest_audio_chunk

Avoid:

frame buffers

historical frame caching

unnecessary image duplication

---

# FACE ENROLLMENT REQUIREMENTS

During enrollment store:

- User ID
- Priority
- Preferred Language
- Face Image
- Face Embedding

Example:

{
    "user_id": "natnael",
    "priority": 2,
    "preferred_language": "amharic"
}

---

# SCENARIO MATCHING REQUIREMENTS

The system must:

- Normalize text
- Match scenarios
- Select prerecorded audio

The system must never:

- Generate text
- Generate responses
- Use embeddings for dialogue search
- Use LLMs

---

# INTERRUPTION HANDLING

Workflow:

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

Resume Original Response

Playback resumes from the previous position.

Playback must not restart.

---

# STREAMLIT REQUIREMENTS

Streamlit is:

- Dashboard
- Monitoring Interface
- Administration Interface

Streamlit is not:

- Face Recognition Engine
- Whisper Engine
- VAD Engine
- Conversation Engine

Business logic must remain in service modules.

---

# LOGGING REQUIREMENTS

Log:

- Startup
- Shutdown
- Face Detection
- Face Recognition
- Greeting Events
- Wake Word Detection
- Scenario Matching
- Playback Events
- Interruptions
- Timeouts
- Face Lost Events
- State Transitions
- Errors
- Warnings

---

# TESTING REQUIREMENTS

Unit Tests:

- Face Recognition
- Scenario Matching
- FSM Transitions

Integration Tests:

- Face Workflow
- Conversation Workflow
- Interruption Workflow

Demonstration Tests:

- Multi-Face Recognition
- Priority Greeting
- Wake Word Detection
- Multilingual Conversations
- Timeout Handling
- Face Lost Handling

---

# SUCCESS CRITERIA

The project is complete only when:

✓ Multiple faces recognized

✓ Users sorted by priority

✓ Sequential greetings work

✓ Greetings use English

✓ Wake words work

✓ English works

✓ Amharic works

✓ Arabic works

✓ Whisper works offline

✓ Scenario matching works

✓ Correct audio responses play

✓ Playback interruption works

✓ Playback resumes correctly

✓ Timeout works

✓ WAITING_FOR_WAKE_WORD persists while faces remain visible

✓ Face disappearance detected

✓ IDLE reached when all faces leave

✓ Runs successfully on Raspberry Pi 4 (8GB)

✓ Complete demonstration succeeds

The final deliverable must be a fully offline, end-to-end, demonstratable conversational robot optimized for Raspberry Pi deployment.
