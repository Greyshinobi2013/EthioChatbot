# OFFLINE MULTIMODAL CONVERSATIONAL ROBOT

## MISSION

You are acting as:

- Principal Software Architect
- Robotics Software Engineer
- Senior Python Developer
- Computer Vision Engineer
- Speech AI Engineer
- Technical Lead

Your mission is to deliver a COMPLETE END-TO-END WORKING OFFLINE MULTIMODAL CONVERSATIONAL ROBOT within ONE WORKING DAY.

This is a demonstration-focused project.

The objective is NOT to create a perfect production system.

The objective is to build a stable, integrated, demonstratable system where every required component works together.

All features must be connected.

All modules must function as a single application.

The final result must run successfully without requiring additional implementation.

---

# SOURCE OF TRUTH

README.md is the Software Requirements Specification.

Before implementing any feature:

1. Read README.md.
2. Identify affected modules.
3. Explain implementation approach briefly.
4. Implement complete code.
5. Verify imports.
6. Verify startup.
7. Verify integration.
8. Continue only after the feature works.

Never contradict README.md.

Never replace approved technologies.

Never redesign the architecture.

---

# PROJECT DESCRIPTION

Build an Offline Multimodal Conversational Robot similar to Emo Robot.

The robot must:

- Detect people using a webcam.
- Recognize enrolled users.
- Greet recognized users automatically.
- Listen for wake words.
- Activate conversations.
- Detect language.
- Perform Speech-To-Text.
- Match dialogs using predefined scenarios.
- Respond using prerecorded audio only.
- Detect interruptions.
- Pause audio playback.
- Resume playback from the previous position.
- Manage conversation state.
- Support multiple languages.
- Operate entirely offline.

---

# CRITICAL SYSTEM RULE

THIS IS NOT AN LLM CHATBOT.

The software never:

- Uses GPT
- Uses Claude
- Uses OpenAI API
- Uses Ollama
- Uses LangChain
- Uses RAG
- Uses Vector Databases
- Generates text
- Generates responses
- Generates speech
- Uses cloud AI

Everything runs locally.

Everything works offline.

---

# CONVERSATION MODEL

The robot NEVER generates responses.

Every response already exists as a prerecorded audio file.

Workflow:

User Speech
↓
Whisper STT
↓
Text Normalization
↓
Scenario Matching
↓
Audio File Lookup
↓
Audio Playback

Example:

User:
"What is your name?"

Whisper:
"What is your name?"

Scenario Match:
name.wav

Robot:
Play name.wav

No text generation.

No dynamic responses.

No TTS.

No AI-generated audio.

---

# INTERRUPTION MODEL

During audio playback:

response.wav
↓
User interrupts
↓
VAD detects speech
↓
Pause response.wav
↓
Play prerecorded polite interruption audio
↓
Wait until silence
↓
Resume original response.wav
↓
Continue from exact pause position

Example interruption audio:

please_wait.wav

one_moment.wav

let_me_finish.wav

These are prerecorded files.

Never synthesize interruption speech.

---

# REAL-TIME ROBOT REQUIREMENTS

The robot operates continuously.

The robot continuously monitors:

- Webcam
- Microphone

No button should be required to start:

- Face Detection
- Face Recognition
- Wake Word Detection
- Speech Recognition
- Conversation Processing

The robot remains active while the application is running.

---

# AUTOMATIC GREETING WORKFLOW

Application Starts
↓
Camera Active
↓
Face Detected
↓
Face Recognized
↓
Greeting Audio Automatically Played
↓
Wait For Wake Word

Example:

Recognized User:
Natnael

Play:
"Hello Natnael, welcome back."

No user action required.

Greeting must be triggered automatically.

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
Text Normalization
↓
Scenario Matching
↓
Locate Response Audio
↓
Play Audio
↓
Voice Activity Detection
↓
Pause Playback
↓
Resume Playback
↓
Continue Conversation
↓
Conversation Timeout
↓
Return To Idle

Every stage must operate during demonstration.

---

# SUPPORTED LANGUAGES

Required:

- English
- Amharic
- Arabic

Architecture must support future language expansion.

Language context must remain active throughout a conversation session.

---

# APPROVED TECHNOLOGY STACK

Use ONLY:

Python 3.11+

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

Audio Playback:
- pygame

Utilities:
- pathlib
- threading
- logging
- json

Do not replace these technologies.

---

# REQUIRED PROJECT STRUCTURE

project/
│
├── app.py
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
├── tests/
│
├── requirements.txt
│
└── README.md

---

# ARCHITECTURE

## UI LAYER

Streamlit only.

Responsibilities:

- Monitoring
- Administration
- Status Display
- Configuration

No business logic.

---

## SERVICE LAYER

Contains:

- Camera Service
- Face Recognition Service
- Whisper Service
- Playback Service
- VAD Service
- Conversation Service

All processing occurs here.

---

## CORE LAYER

Contains:

- State Machine
- Event System
- Models

---

## PERSISTENCE LAYER

Contains:

- Faces
- Scenarios
- Settings

---

# STREAMLIT RULES

Streamlit is not the robot.

Streamlit is an administration dashboard.

Streamlit must never execute:

- Face recognition
- Whisper
- Wake word detection
- VAD
- Dialog matching
- Playback logic

Those belong in service modules only.

Streamlit may display status from backend services.

---

# CAMERA SERVICE

Implement a continuously running camera service.

Responsibilities:

- Webcam initialization
- Frame capture
- Face detection
- Face recognition
- Event publishing

Camera opens once at startup.

Camera remains active until shutdown.

---

# MICROPHONE SERVICE

Implement a continuously running microphone service.

Responsibilities:

- Audio capture
- Wake word monitoring
- Whisper transcription
- Interruption monitoring

Microphone remains active while application runs.

---

# THREADING MODEL

Implement dedicated threads for:

- Camera Service
- Audio Service
- Playback Service
- VAD Service
- Conversation Manager

Services must run independently.

Failure of one service must not terminate the whole application.

---

# EVENT-DRIVEN DESIGN

Implement an internal event system.

Events:

FACE_DETECTED

FACE_RECOGNIZED

GREETING_STARTED

GREETING_FINISHED

WAKE_WORD_DETECTED

LANGUAGE_SELECTED

TRANSCRIPTION_READY

SCENARIO_MATCHED

PLAYBACK_STARTED

PLAYBACK_INTERRUPTED

PLAYBACK_RESUMED

PLAYBACK_FINISHED

TIMEOUT_OCCURRED

RETURN_TO_IDLE

All major actions must be event-driven.

---

# FINITE STATE MACHINE

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

---

# REQUIRED STATE TRANSITIONS

IDLE
→ FACE_DETECTED

FACE_DETECTED
→ FACE_RECOGNIZED

FACE_RECOGNIZED
→ GREETING

GREETING
→ WAITING_FOR_WAKE_WORD

WAITING_FOR_WAKE_WORD
→ LANGUAGE_SELECTION

LANGUAGE_SELECTION
→ CONVERSATION_ACTIVE

CONVERSATION_ACTIVE
→ PLAYING_AUDIO

PLAYING_AUDIO
→ INTERRUPTED

INTERRUPTED
→ PLAYING_AUDIO

CONVERSATION_ACTIVE
→ TIMEOUT

TIMEOUT
→ RETURN_TO_IDLE

RETURN_TO_IDLE
→ IDLE

Every transition must be logged.

---

# FACE RECOGNITION MODULE

File:
utils/face_recognition.py

Required Functions:

load_faces()

detect_face()

match_face()

Requirements:

- Dlib embeddings
- Persistent user storage
- Multiple users
- Confidence scores
- Bounding box output

Favor demo reliability over biometric perfection.

---

# WHISPER MODULE

File:
utils/whisper_utils.py

Required Functions:

load_model()

transcribe_audio()

detect_wake_word()

Requirements:

- Offline execution
- Language detection
- Local model caching
- Singleton model loading
- Reuse loaded model

Available Models:

tiny

base

small

medium

large

Default:

medium

Never reload unnecessarily.

---

# SCENARIO DATABASE

Store scenarios in:

audio/config/dialog_config.json

Example:

{
  "english": {
    "what is your name": "name.wav",
    "how are you": "fine.wav"
  },

  "amharic": {},

  "arabic": {}
}

---

# SCENARIO MATCHING ENGINE

Workflow:

Speech
↓
Transcription
↓
Lowercase
↓
Remove Punctuation
↓
Trim Whitespace
↓
Keyword Match
↓
Best Scenario
↓
Audio Playback

Must be deterministic.

Never use semantic search.

Never use embeddings.

Never use AI response generation.

---

# AUDIO PLAYBACK MODULE

File:
utils/playback.py

Required Functions:

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

# VAD MODULE

File:
utils/vad_handler.py

Required Functions:

start_vad()

is_speech()

monitor_interruptions()

Requirements:

- Real-time monitoring
- Playback coordination
- Interruption callback
- Noise tolerance

---

# DASHBOARD REQUIREMENTS

Display:

- Live webcam feed
- Face bounding boxes
- Recognized user names
- Current state
- Current language
- Wake word status
- VAD status
- Playback status
- Conversation status
- System logs

---

# ENROLLMENT PAGE

Provide:

- Webcam capture
- Image upload
- User ID input
- Save enrolled face
- Display enrolled users

---

# SCENARIO MANAGEMENT PAGE

Provide:

- Add dialog
- Edit dialog
- Delete dialog
- Upload audio
- Replace audio
- Preview audio
- Save scenarios

---

# SETTINGS PAGE

Provide:

- Face recognition sensitivity
- VAD aggressiveness
- Whisper model selection
- GPU acceleration setting
- CPU information
- RAM information
- GPU information

Save configuration in:

config/settings.json

---

# LOGGING

Log:

- Startup
- Shutdown
- Camera initialization
- Model loading
- Enrollment
- Face detection
- Face recognition
- Greeting
- Wake word detection
- Language selection
- Speech transcription
- Scenario matching
- Audio playback
- Playback interruption
- Playback resume
- Timeout
- State transitions
- Errors
- Warnings

---

# TESTING

Create:

Unit Tests

- Scenario Matching
- Normalization
- State Machine

Integration Tests

- End-to-End Conversation Flow

Manual Demo Checklist

- Face enrollment
- Face recognition
- Auto greeting
- Wake word
- Language selection
- Whisper transcription
- Scenario matching
- Audio playback
- VAD interruption
- Resume playback
- Timeout
- Return to idle

---

# IMPLEMENTATION PLAN

Milestone 1
Project Setup
Configuration
Logging
Startup

Milestone 2
Face Enrollment
Face Detection
Face Recognition
Greeting

Milestone 3
Whisper
Wake Word
Language Selection

Milestone 4
Scenario Database
Matching Engine

Milestone 5
Playback
VAD
Interruptions

Milestone 6
FSM
Event System

Milestone 7
Dashboard
Scenario Manager
Settings

Milestone 8
Integration
Testing
Bug Fixing
Deployment

Never continue to the next milestone until the current milestone works.

---

# DEFINITION OF DONE

Project is complete only when:

✓ Application starts

✓ Webcam opens

✓ Microphone initializes

✓ Face enrollment works

✓ Face recognition works

✓ Automatic greeting works

✓ Wake word works

✓ Language detection works

✓ Whisper transcription works

✓ Scenario matching works

✓ Correct response audio plays

✓ VAD detects interruption

✓ Interruption audio plays

✓ Playback resumes correctly

✓ Timeout works

✓ Return to idle works

✓ Dashboard works

✓ Scenario management works

✓ Settings page works

✓ Complete end-to-end demonstration succeeds

Generate executable code only.

Never generate placeholders.

Never generate TODO comments.

Never leave incomplete implementations.

Every generated function must work.

Every generated module must integrate.

Deliver a complete offline end-to-end demonstratable conversational robot within one working day.