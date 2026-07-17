# EthioChatbot V2 Demonstration Script

## Purpose

This document defines the official demonstration workflow for EthioChatbot V2.

The project is considered successful only when the entire workflow executes from beginning to end without errors.

This script represents the expected real-world operation of the robot.

All demonstration scenarios must run entirely offline.

---

# Demonstration Objective

Demonstrate:

- Multi-face recognition
- Priority-based greetings
- Personalized greetings
- Wake-word activation
- Multilingual conversations
- Scenario matching
- Audio playback
- Interruption handling
- Playback resume
- Face persistence
- Conversation timeout
- Return to idle

---

# System Preconditions

Before beginning the demonstration:

Verify:

✓ Application starts successfully

✓ Webcam is active

✓ Microphone is active

✓ Audio output device works

✓ Whisper model loads

✓ Face database exists

✓ Scenario database exists

✓ Greeting audio exists

✓ Response audio exists

✓ Interruption audio exists

---

# Demo Scenario

The demonstration uses three enrolled users.

Example:

Manager

Priority: 1

Preferred Language: English

---

Natnael

Priority: 2

Preferred Language: Amharic

---

Visitor

Priority: 3

Preferred Language: Arabic

---

# STEP 1

## System Startup

Action:

Launch EthioChatbot V2.

Expected Result:

- Configuration loads
- Event Bus initializes
- Whisper model loads
- Camera starts
- Microphone starts
- FSM enters IDLE

PASS:

Robot enters IDLE successfully.

---

# STEP 2

## Multi-Face Detection

Action:

Place three enrolled users in front of the camera.

Expected Result:

Faces detected.

Recognized Users:

- Manager
- Natnael
- Visitor

PASS:

All visible enrolled users are recognized.

---

# STEP 3

## Priority Sorting

Action:

Wait for recognition to complete.

Expected Result:

Users sorted by priority.

Order:

Manager (1)

↓

Natnael (2)

↓

Visitor (3)

PASS:

Priority order matches enrollment data.

---

# STEP 4

## Sequential Greeting

Action:

Allow greeting workflow to begin.

Expected Result:

Robot greets users sequentially.

Example:

Hello Manager.

↓

Hello Natnael.

↓

Hello Visitor.

Language:

English

PASS:

Greetings follow priority order.

PASS:

Greetings occur automatically.

---

# STEP 5

## Enter Wake Word State

Expected Result:

FSM transitions to:

WAITING_FOR_WAKE_WORD

Robot begins listening.

PASS:

Wake-word waiting state becomes active.

---

# STEP 6

## English Wake Word

Action:

Speak:

Hello Robot

Expected Result:

WAKE_WORD_DETECTED

Language:

English

FSM:

CONVERSATION_ACTIVE

PASS:

English session activates.

---

# STEP 7

## English Question

Action:

Speak:

What is your name?

Expected Result:

Whisper transcribes speech.

Scenario engine matches:

what is your name

Selected Response:

audio/english/name.wav

Robot plays response.

PASS:

Correct English response plays.

---

# STEP 8

## English Interruption

Action:

Speak while response audio is playing.

Expected Result:

Playback pauses.

Robot plays:

please_wait.wav

PASS:

Playback pauses.

PASS:

Interruption audio plays.

---

# STEP 9

## Resume Playback

Action:

Remain silent.

Expected Result:

Silence detected.

Original response resumes.

Original response continues from previous position.

PASS:

Response resumes correctly.

PASS:

Playback does not restart.

---

# STEP 10

## Conversation Timeout

Action:

Remain silent.

Expected Result:

Timeout occurs.

FSM enters:

TIMEOUT

Conversation context cleared.

PASS:

Timeout occurs successfully.

---

# STEP 11

## Return To Waiting State

Expected Result:

FSM enters:

WAITING_FOR_WAKE_WORD

Reason:

Recognized users remain visible.

Robot continues listening.

PASS:

Robot does not return to IDLE.

PASS:

Robot remains available.

---

# STEP 12

## Amharic Conversation

Action:

Speak:

ሰላም ሮቦት

Expected Result:

Language determined:

Amharic

FSM enters:

CONVERSATION_ACTIVE

PASS:

Amharic session activates.

---

# STEP 13

## Amharic Scenario

Action:

Speak an Amharic question that exists in the scenario database.

Example:

ስምህ ማን ነው

Expected Result:

Scenario matched.

Amharic response selected.

Audio plays.

PASS:

Correct Amharic audio plays.

---

# STEP 14

## Timeout Again

Action:

Remain silent.

Expected Result:

Conversation timeout.

FSM:

WAITING_FOR_WAKE_WORD

PASS:

Wake-word state restored.

---

# STEP 15

## Arabic Conversation

Action:

Speak:

مرحبا روبوت

Expected Result:

Language determined:

Arabic

FSM enters:

CONVERSATION_ACTIVE

PASS:

Arabic session activates.

---

# STEP 16

## Arabic Scenario

Action:

Speak an Arabic question that exists in the scenario database.

Example:

ما اسمك

Expected Result:

Arabic scenario matched.

Arabic audio selected.

Audio plays.

PASS:

Correct Arabic audio plays.

---

# STEP 17

## Face Persistence Test

Action:

Keep one recognized user visible.

Example:

Natnael remains visible.

Expected Result:

Robot remains in:

WAITING_FOR_WAKE_WORD

PASS:

Robot remains active.

PASS:

No additional greeting occurs.

---

# STEP 18

## Partial Face Loss

Action:

Manager leaves camera view.

Visitor leaves camera view.

Natnael remains visible.

Expected Result:

FACE_LOST events generated.

Active user list updated.

Robot remains:

WAITING_FOR_WAKE_WORD

PASS:

Robot continues operating.

PASS:

No return to IDLE.

---

# STEP 19

## Complete Face Loss

Action:

Natnael leaves camera view.

No recognized users remain visible.

Wait for configured face-lost timeout.

Expected Result:

FACE_LOST

↓

ALL_USERS_LOST

↓

RETURN_TO_IDLE

↓

IDLE

PASS:

Robot returns to idle.

---

# STEP 20

## Re-Entry Test

Action:

Natnael returns to camera view.

Expected Result:

Recognition occurs again.

Greeting workflow restarts.

PASS:

Recognition cycle restarts successfully.

PASS:

System behaves consistently after returning to IDLE.

---

# Success Criteria

The demonstration succeeds when all of the following work:

✓ Multiple faces detected

✓ Multiple users recognized

✓ Priority sorting works

✓ Greeting sequence works

✓ Greetings use English

✓ Wake words detected

✓ English conversation works

✓ Amharic conversation works

✓ Arabic conversation works

✓ Whisper STT works

✓ Scenario matching works

✓ Correct audio plays

✓ Interruption detection works

✓ Playback pauses

✓ Interruption audio plays

✓ Playback resumes

✓ Playback resumes from stored position

✓ Timeout occurs

✓ WAITING_FOR_WAKE_WORD persists while users remain visible

✓ FACE_LOST events occur correctly

✓ Robot returns to IDLE when all users leave

✓ Recognition cycle restarts when users return

---

# Final Demonstration Result

EthioChatbot V2 is considered demonstration-ready when the entire workflow completes successfully without:

- Application restart
- Manual intervention
- Service crashes
- Missing audio
- Failed state transitions
- Failed language sessions

The final demonstration must show a fully offline multilingual conversational robot operating correctly on Raspberry Pi 4 (8GB) deployment hardware.
