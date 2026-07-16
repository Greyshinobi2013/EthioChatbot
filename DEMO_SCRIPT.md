# DEMONSTRATION SCRIPT

## Purpose

This file defines the demonstration workflow.

The project is considered successful only when every step can be performed from beginning to end.

---

# Step 1

Launch Application

Expected Result:

- Application starts
- Configuration loads
- Logging starts
- Webcam initializes
- Microphone initializes
- FSM enters IDLE

PASS if application remains running.

---

# Step 2

Enroll User Face

Action:

- Open Enrollment Page
- Capture face
- Save user

Expected Result:

- Face stored successfully
- User appears in enrolled users list

PASS if user enrollment succeeds.

---

# Step 3

Recognize User

Action:

- Present enrolled face to webcam

Expected Result:

- Face detected
- Face recognized
- User name displayed

PASS if recognition succeeds.

---

# Step 4

Automatic Greeting

Expected Result:

- Greeting audio automatically plays

PASS if greeting plays without user interaction.

---

# Step 5

Wait For Wake Word

Expected Result:

- FSM enters WAITING_FOR_WAKE_WORD

PASS if robot is listening.

---

# Step 6

Speak Wake Word

Example:

Hello Robot

Expected Result:

- Wake word detected
- Wake word event generated

PASS if wake word is recognized.

---

# Step 7

Language Selection

Example:

English

Expected Result:

- Language set to English
- FSM enters CONVERSATION_ACTIVE

PASS if language state updates.

---

# Step 8

Ask a Question

Example:

What is your name?

Expected Result:

- Whisper transcribes speech
- Scenario matched
- name.wav selected

PASS if correct scenario is found.

---

# Step 9

Play Response

Expected Result:

- Audio starts

PASS if correct prerecorded response plays.

---

# Step 10

Interrupt Robot

Action:

Speak while response is playing.

Expected Result:

- VAD detects speech
- Playback pauses
- please_wait.wav plays

PASS if interruption is detected.

---

# Step 11

Become Silent

Expected Result:

- Silence detected
- Original response resumes

PASS if resume occurs from previous position.

---

# Step 12

Wait For Timeout

Expected Result:

- Timeout reached
- FSM transitions to TIMEOUT

PASS if timeout occurs.

---

# Step 13

Return To Idle

Expected Result:

- RETURN_TO_IDLE state entered
- IDLE state entered

PASS if robot returns to listening mode.

---

# Demonstration Success Criteria

The demonstration is successful only if:

✓ Face enrollment works

✓ Face recognition works

✓ Greeting works

✓ Wake word works

✓ Language selection works

✓ Whisper works

✓ Scenario matching works

✓ Audio playback works

✓ Interruption handling works

✓ Playback resumes

✓ Timeout works

✓ Return to idle works

✓ Application remains stable throughout demonstration
``