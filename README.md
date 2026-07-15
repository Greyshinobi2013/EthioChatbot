# ROLE

You are a Principal AI Software Architect, Robotics Engineer, Computer Vision Engineer, Speech AI Engineer, and Senior Python Developer.

Your task is to design and implement a complete production-quality Offline Multimodal Conversational Robot similar to Emo Robot.

The system must be:

- Fully offline
- Modular
- Extensible
- Production-ready
- Maintainable
- Event-driven
- Streamlit-based
- Server-side processing only

The goal is to deliver a complete working software system, not example code snippets.

---

# PROJECT NAME

Offline Multimodal Conversational Robot

---

# PROJECT OBJECTIVE

Build an intelligent conversational robot capable of:

1. Detecting people using a webcam.
2. Recognizing enrolled users.
3. Greeting recognized users.
4. Listening for ignition words.
5. Activating a conversation session.
6. Detecting spoken language.
7. Performing Speech-to-Text using Whisper.
8. Matching user speech against predefined dialog scenarios.
9. Responding with prerecorded audio.
10. Detecting interruptions while speaking.
11. Pausing and resuming audio playback.
12. Managing conversation state.
13. Supporting multiple languages.
14. Operating entirely offline.

The conversational behaviour should emulate Emo Robot.

---

# SUPPORTED LANGUAGES

The system must support:

- English
- Amharic (አማርኛ)
- Arabic (العربية)

The architecture must allow future language expansion.

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
Waiting For Ignition Word
    ↓
Wake Word Detection
    ↓
Language Selection
    ↓
Conversation Activated
    ↓
Speech To Text
    ↓
Dialog Matching
    ↓
Audio Playback
    ↓
Interruption Detection
    ↓
Pause Playback
    ↓
Resume Playback
    ↓
Conversation Continues
    ↓
Timeout
    ↓
Return To Idle

---

# PROJECT STRUCTURE

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
│   │
│   └── config/
│       └── dialog_config.json
│
├── pages/
│   ├── 1_Dashboard.py
│   ├── 2_Enroll_Face.py
│   ├── 3_Manage_Scenarios.py
│   └── 4_Settings.py
│
├── config/
│   └── settings.json
│
├── utils/
│   ├── face_recognition.py
│   ├── vad_handler.py
│   ├── whisper_utils.py
│   ├── playback.py
│   ├── conversation_manager.py
│   ├── state_manager.py
│   └── logger.py
│
├── models/
│
├── requirements.txt
│
└── README.md

---

# TECHNOLOGY STACK

Frontend:
- Streamlit

Computer Vision:
- OpenCV
- Dlib
- NumPy

Speech-to-Text:
- OpenAI Whisper

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

Language:
- Python 3.11+

---

# DASHBOARD REQUIREMENTS

File:

pages/1_Dashboard.py

Purpose:

Runtime monitoring and control.

Features:

## Webcam Feed

Display:

- Live webcam stream
- Face bounding boxes
- Recognized user names

Use:

load_faces()
detect_face()
match_face()

---

## Status Cards

Display:

- System Status
- Recognized User
- Current Language
- Wake Word Status
- VAD Status
- Playback Status
- Conversation Status

---

## Conversation Monitoring

Display:

Current state:

- IDLE
- FACE_RECOGNIZED
- WAITING_FOR_WAKE_WORD
- CONVERSATION_ACTIVE
- PLAYING_RESPONSE
- INTERRUPTED

---

## System Log

Continuously log:

- Face detected
- Face recognized
- Greeting played
- Wake word detected
- Language selected
- Conversation activated
- Dialog matched
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
- Photo upload
- User ID input
- Save image to faces/
- Validate enrollment
- Display enrolled users

---

# SCENARIO MANAGEMENT REQUIREMENTS

File:

pages/3_Manage_Scenarios.py

Purpose:

Conversation Authoring Tool

NOT a playback page.

Administrators must be able to:

## Language Management

English

Amharic

Arabic

---

## Ignition Word Management

Add ignition word

Edit ignition word

Delete ignition word

Examples:

English

- hello robot
- hey robot
- computer

Amharic

- ሰላም ሮቦት
- ሄይ ሮቦት

Arabic

- مرحبا روبوت
- أهلا روبوت
- يا روبوت

---

## Dialog Management

Each dialog contains:

{
    "user_text": "",
    "response_audio": ""
}

Administrator can:

- Add dialog
- Edit dialog
- Delete dialog
- Upload audio
- Replace audio
- Preview audio
- Save scenario

---

## Scenario Storage

audio/config/dialog_config.json

Example:

{
  "english": {

    "ignition_words": [
      "hello robot",
      "hey robot"
    ],

    "dialogs": [

      {
        "user_text":
        "what is your name",

        "response_audio":
        "audio/english/name.wav"
      },

      {
        "user_text":
        "how are you",

        "response_audio":
        "audio/english/how_are_you.wav"
      }

    ]
  },

  "amharic": {

    "ignition_words": [
      "ሰላም ሮቦት"
    ],

    "dialogs": [

      {
        "user_text":
        "ስምህ ማነው",

        "response_audio":
        "audio/amharic/name.wav"
      }

    ]
  },

  "arabic": {

    "ignition_words": [
      "مرحبا روبوت"
    ],

    "dialogs": [

      {
        "user_text":
        "ما اسمك",

        "response_audio":
        "audio/arabic/name.wav"
      }

    ]
  }
}

---

# SETTINGS REQUIREMENTS

File:

pages/4_Settings.py

Features:

- Face recognition sensitivity
- VAD aggressiveness
- Whisper model selection
- GPU acceleration
- CPU information
- RAM information
- GPU information
- Save settings

Store:

config/settings.json

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
- Persistent enrolled users
- Multiple user support
- Bounding box output
- Confidence scoring

---

# WHISPER MODULE

File:

utils/whisper_utils.py

Functions:

load_model()

transcribe_audio()

detect_wake_word()

Requirements:

- Local model caching
- Offline execution
- Language detection
- English support
- Amharic support
- Arabic support

Available models:

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
- Interruption callback
- Playback coordination
- Noise resilience

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
- Pause
- Resume
- Restart
- Playback state tracking

---

# CONVERSATION MANAGER

File:

utils/conversation_manager.py

Create a finite-state machine.

States:

IDLE

FACE_RECOGNIZED

WAITING_FOR_WAKE_WORD

CONVERSATION_ACTIVE

PLAYING_RESPONSE

INTERRUPTED

TIMEOUT

Responsibilities:

- State transitions
- Wake word activation
- Dialog matching
- Timeout control
- Language context
- Playback coordination

---

# CONVERSATION BEHAVIOR

Example:

User appears

↓

Face recognized

↓

Greeting audio

↓

System waits

User:

"Hello robot"

↓

Wake word detected

↓

Conversation activated

User:

"What is your name?"

↓

Whisper transcription

↓

Scenario match

↓

Play name.wav

↓

User interrupts

↓

Pause playback

↓

Notify:

"Please wait."

↓

User becomes silent

↓

Resume playback

↓

Conversation continues

↓

Timeout

↓

Return to wake word listening

---

# SOFTWARE QUALITY REQUIREMENTS

Generate production-grade code.

Requirements:

- Python type hints
- Modular architecture
- SOLID principles
- Clean code
- Logging
- Error handling
- Thread safety
- Session state management
- No hard-coded values
- Configuration-driven behavior

---

# OUTPUT REQUIREMENTS

Generate:

1. Complete folder structure.
2. Complete source code for every file.
3. requirements.txt.
4. README.md.
5. JSON configuration files.
6. Streamlit pages.
7. Utility modules.
8. State machine implementation.
9. Logging framework.
10. Deployment instructions.

Do not produce partial implementations.

Generate a complete working project.
