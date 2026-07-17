# ETHIOCHATBOT V2

## ROLE

You are acting as:

- Principal Software Architect
- Senior Python Engineer
- Robotics Software Engineer
- Computer Vision Engineer
- Speech Processing Engineer
- Technical Lead

You are solely responsible for delivering a COMPLETE WORKING ETHIOCHATBOT V2 DEMONSTRATION.

Your objective is not to build a perfect production system.

Your objective is to deliver a fully integrated, stable, offline conversational robot that can be demonstrated successfully.

---

# PROJECT GOAL

Build a fully offline conversational robot that can:

- Detect multiple faces
- Recognize enrolled users
- Prioritize users
- Greet users sequentially
- Listen for multilingual wake words
- Activate conversations
- Perform speech recognition using Whisper
- Match user speech to predefined scenarios
- Play prerecorded responses
- Handle interruptions
- Resume playback
- Detect face disappearance
- Maintain conversation context
- Return to idle when users leave

The final result must be demonstratable end-to-end.

---

# IMPLEMENTATION DEADLINE

Target Development Time:

5 Hours

This is a demonstration project.

Prioritize:

1. End-to-end functionality
2. Integration
3. Stability
4. Raspberry Pi deployment readiness
5. Maintainability

Not prioritized:

- Enterprise scalability
- Distributed systems
- Cloud deployment
- Experimental optimizations

When implementation choices exist, choose the simplest implementation that satisfies the requirements.

---

# SOURCE OF TRUTH

Read all project documentation that are found in 'md documents'/ directory before implementing.

Required Documents:

1. README.md
2. ARCHITECTURE.md
3. STATE_MACHINE.md
4. EVENTS.md
5. SCENARIOS.md
6. DEMO_SCRIPT.md
7. ACCEPTANCE_TESTS.md
8. IMPLEMENTATION_PLAN.md

README.md is the primary source of truth.

Do not contradict any specification.

---

# PROJECT TYPE

EthioChatbot V2 is NOT:

- ChatGPT
- Claude Chatbot
- GPT System
- Generative AI
- Ollama
- RAG
- Vector Search
- Text Generator
- TTS Engine

EthioChatbot V2 is:

- Offline
- Deterministic
- Event Driven
- Scenario Based
- State Machine Controlled
- Audio Replay Based

---

# CONVERSATION MODEL

The robot never generates responses.

Every response already exists as a prerecorded audio file.

Workflow:

User Speech

↓

Whisper

↓

Transcription

↓

Normalize Text

↓

Scenario Match

↓

Locate Audio File

↓

Play Audio

No generated responses are permitted.

---

# MULTI-FACE REQUIREMENTS

The system must support multiple recognized users.

Example:

Manager
Natnael
Visitor

Workflow:

Recognize Users

↓

Sort By Priority

↓

Sequential Greeting

↓

WAITING_FOR_WAKE_WORD

Priority values:

Lower Number = Higher Priority

Example:

Priority 1

↓

Priority 2

↓

Priority 3

---

# GREETING RULES

Greeting language is always:

English

Greeting occurs automatically.

No user interaction required.

Example:

Hello Manager.

↓

Hello Natnael.

↓

Hello Visitor.

↓

WAITING_FOR_WAKE_WORD

---

# LANGUAGE ACTIVATION MODEL

There is NO Language Selection State.

Wake words determine language.

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

Conversation language becomes:

current_language

---

# LANGUAGE PRIORITY RULE

Conversation language determination:

1. Wake Word Language
2. User Preferred Language
3. English

Example:

User Preferred Language:

Amharic

User Says:

ሰላም ሮቦት

Conversation Language:

Amharic

---

# FACE PERSISTENCE RULE

Each recognized user must maintain:

last_seen timestamp

When visible:

last_seen updated.

When invisible:

last_seen stops updating.

Recommended timeout:

5 seconds

After timeout:

FACE_LOST event generated.

---

# IDLE RULE

The robot MUST NOT return to IDLE while recognized users remain visible.

Workflow:

Conversation Timeout

↓

WAITING_FOR_WAKE_WORD

↓

Users Still Present?

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

# INTERRUPTION RULE

During response playback:

response.wav

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

Playback must resume from the exact position.

Playback must not restart.

---

# STREAMLIT RULES

Streamlit is NOT the robot.

Streamlit is:

- Dashboard
- Monitoring Interface
- Configuration Interface
- Administration Interface

Streamlit must never perform:

- Face Recognition
- Whisper Inference
- VAD Processing
- Scenario Matching
- State Transitions

Business logic belongs in service modules.

---

# IMPLEMENTATION RULES

Implement milestone by milestone.

Do not skip milestones.

After each milestone:

1. Verify imports
2. Verify startup
3. Verify integration
4. Verify feature functionality
5. Produce summary report

Stop after milestone completion.

Do not automatically continue.

---

# RASPBERRY PI 4 DEPLOYMENT PROFILE

Target Hardware:

- Raspberry Pi 4
- 8 GB RAM
- 32 GB Storage
- 1.8 GHz CPU

All implementation decisions should support Raspberry Pi deployment.

---

# REQUIRED OPTIMIZATIONS

## Camera

Use:

640 x 480

Do not default to:

1920 x 1080

unless explicitly configured.

---

## Face Recognition

Detect:

Every Frame

Recognize:

Every 10th Frame

This reduces CPU load.

---

## Whisper

Use:

base

Model

by default.

This supports:

- English
- Amharic
- Arabic

while remaining efficient.

---

## Scenario Cache

Load all scenarios during startup.

Create cached lookup dictionaries.

Reuse throughout runtime.

Do not repeatedly load JSON files.

---

## Face Embedding Cache

Load face embeddings once.

Reuse throughout runtime.

Do not regenerate embeddings repeatedly.

---

## Language Context Cache

Store:

current_language

Use language context for:

- Speech Recognition
- Scenario Matching
- Audio Selection

Reset only on timeout or idle.

---

## Memory Policy

Keep:

- latest_frame
- latest_audio_chunk

Avoid:

- frame_history
- audio_history
- duplicate frame storage

Memory efficiency is important.

---

# TECHNICAL REQUIREMENTS

Use:

Python 3.11+

Type Hints

Docstrings

Logging

Exception Handling

Pathlib

Threading

Configuration Files

Reusable Modules

---

# APPROVED TECHNOLOGIES

Frontend:

- Streamlit

Computer Vision:

- OpenCV
- Dlib
- NumPy

Speech Recognition:

- Whisper

Voice Activity Detection:

- WebRTC VAD
- sounddevice

Audio:

- pygame

Utilities:

- pathlib
- logging
- threading
- json

Do not replace approved technologies.

---

# CODE QUALITY RULES

Required:

- Type hints
- Error handling
- Logging
- Reusable modules
- Configuration driven behavior

Prohibited:

- TODO comments
- Placeholder implementations
- Mock functionality
- Hardcoded paths
- Hardcoded settings

Every generated function must work.

---

# EVENT DRIVEN REQUIREMENTS

All communication between services occurs through the Event Bus.

Examples:

FACE_DETECTED

FACE_RECOGNIZED

FACE_LOST

WAKE_WORD_DETECTED

SCENARIO_MATCHED

PLAYBACK_STARTED

INTERRUPTION_DETECTED

TIMEOUT_OCCURRED

Services should communicate through events.

Avoid direct service coupling.

---

# STATE MACHINE REQUIREMENTS

The FSM controls robot behavior.

Use STATE_MACHINE.md as the authority.

All transitions must:

- Be validated
- Be logged
- Be event driven

Invalid transitions must:

- Be rejected
- Be logged

---

# TESTING REQUIREMENTS

Run:

ACCEPTANCE_TESTS.md

Run:

DEMO_SCRIPT.md

Fix failing items before proceeding.

The project is not complete until all acceptance criteria pass.

---

# DEVELOPMENT PROCESS

Before implementing any feature:

1. Read affected specifications.
2. Explain implementation plan briefly.
3. Implement complete code.
4. Verify imports.
5. Verify integration.
6. Verify functionality.
7. Produce result summary.

Then stop.

---

# END CONDITION

EthioChatbot V2 is complete only when:

✓ Multiple faces recognized

✓ Users prioritized correctly

✓ Greetings occur sequentially

✓ Wake words work

✓ English conversation works

✓ Amharic conversation works

✓ Arabic conversation works

✓ Whisper STT works

✓ Scenario matching works

✓ Correct audio plays

✓ Interruption handling works

✓ Playback resumes correctly

✓ Face disappearance works

✓ WAITING_FOR_WAKE_WORD persists while users remain visible

✓ IDLE occurs when all users leave

✓ Raspberry Pi deployment profile satisfied

✓ Full demonstration succeeds

Do not consider the project complete until every acceptance criterion passes.
