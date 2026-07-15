# Demonstration Script

This script represents the required end-to-end demonstration.

---

## Step 1

Start Application

Expected Result:

Dashboard loads successfully.

System enters IDLE state.

---

## Step 2

Present Registered User

Expected Result:

Face detected.

Face recognized.

User name displayed.

---

## Step 3

Automatic Greeting

Expected Result:

Greeting audio plays automatically.

System enters WAITING_FOR_WAKE_WORD.

---

## Step 4

Say Wake Word

Example:

Hello Robot

Expected Result:

Wake word detected.

LANGUAGE_SELECTION state entered.

---

## Step 5

Select Language

Example:

English

Expected Result:

Language context set.

Conversation activated.

---

## Step 6

Ask Question

Example:

What is your name?

Expected Result:

Whisper transcription.

Scenario match.

Correct audio response.

---

## Step 7

Interrupt Playback

Speak while audio is playing.

Expected Result:

Playback paused.

Interruption audio played.

---

## Step 8

Become Silent

Expected Result:

Playback resumes from previous location.

---

## Step 9

Wait For Timeout

Expected Result:

Conversation timeout occurs.

Return to idle state.

---

## Success Criteria

Entire workflow completes without restarting the application.