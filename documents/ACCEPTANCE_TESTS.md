# EthioChatbot V2 Acceptance Tests

## Purpose

This document defines the official acceptance criteria for EthioChatbot V2.

The project is considered complete only when ALL acceptance tests pass.

No feature is considered complete until its acceptance criteria succeed.

The goal of these tests is to verify:

- End-to-end functionality
- Offline operation
- Multilingual support
- Raspberry Pi compatibility
- Demonstration readiness

---

# Acceptance Rules

A test is considered:

PASS

when expected behavior occurs consistently.

A test is considered:

FAIL

when:

- Functionality is missing
- Functionality is unstable
- Errors occur
- Manual intervention is required

---

# SECTION 1

# Application Startup Tests

## Startup

[ ] Application launches successfully

[ ] Streamlit dashboard loads

[ ] Configuration loads successfully

[ ] Shared state initializes

[ ] Event Bus initializes

[ ] State Machine initializes

[ ] Logging initializes

[ ] Application enters IDLE state

---

## Hardware Initialization

[ ] Webcam initializes successfully

[ ] Webcam remains active

[ ] Microphone initializes successfully

[ ] Audio device initializes successfully

[ ] Hardware remains operational after startup

---

## Service Initialization

[ ] Camera Service starts

[ ] Audio Service starts

[ ] Face Recognition Service starts

[ ] Whisper Service starts

[ ] VAD Service starts

[ ] Playback Service starts

[ ] Conversation Service starts

---

# SECTION 2

# Database Loading Tests

## Face Database

[ ] Face database loads

[ ] User metadata loads

[ ] Face embeddings load

[ ] No duplicate loading

---

## Scenario Database

[ ] dialog_config.json loads

[ ] English scenarios load

[ ] Amharic scenarios load

[ ] Arabic scenarios load

[ ] Scenario cache created

---

## Settings

[ ] settings.json loads

[ ] Camera settings load

[ ] Whisper settings load

[ ] VAD settings load

[ ] Timeout settings load

---

# SECTION 3

# Face Enrollment Tests

## Enrollment

[ ] Webcam enrollment works

[ ] Image upload works

[ ] Face image stored

[ ] Face embedding generated

[ ] User ID stored

[ ] Priority stored

[ ] Preferred language stored

---

## Validation

[ ] User appears in enrollment list

[ ] Stored metadata is correct

[ ] Stored image exists

[ ] Stored embedding exists

---

# SECTION 4

# Multi-Face Detection Tests

## Face Detection

[ ] Single face detection works

[ ] Multiple face detection works

[ ] Face count returned correctly

---

## Recognition

[ ] Single-user recognition works

[ ] Multi-user recognition works

[ ] Confidence score generated

[ ] Unknown face rejection works

---

## User Activation

[ ] Active user list updates correctly

[ ] Multiple active users supported

---

# SECTION 5

# Priority System Tests

## Priority Loading

[ ] Priority data loads correctly

[ ] Priorities retrieved successfully

---

## Sorting

[ ] Users sorted correctly

[ ] Priority 1 appears first

[ ] Priority 2 appears second

[ ] Priority 3 appears third

---

## Queue Building

[ ] Greeting queue created

[ ] Queue order matches priority order

---

# SECTION 6

# Greeting Workflow Tests

## Automatic Greeting

[ ] Greeting starts automatically

[ ] Greeting state entered

[ ] Greeting audio exists

[ ] Greeting audio plays

---

## Sequential Greeting

[ ] User 1 greeted

[ ] User 2 greeted

[ ] User 3 greeted

[ ] Greeting order follows priority

---

## Greeting Language

[ ] Greeting uses English

[ ] Greeting ignores preferred language

[ ] Greeting completes successfully

---

## Greeting Completion

[ ] GREETING_FINISHED event generated

[ ] FSM enters WAITING_FOR_WAKE_WORD

---

# SECTION 7

# Wake Word Detection Tests

## English Wake Words

[ ] Hello Robot detected

[ ] Hey Robot detected

[ ] Computer detected

---

## Amharic Wake Words

[ ] ሰላም ሮቦት detected

[ ] ሄይ ሮቦት detected

---

## Arabic Wake Words

[ ] مرحبا روبوت detected

[ ] أهلا روبوت detected

---

## Invalid Wake Words

[ ] Invalid wake words rejected

[ ] No false activations

---

# SECTION 8

# Language Context Tests

## English Session

[ ] English wake word creates English session

[ ] current_language set to English

---

## Amharic Session

[ ] Amharic wake word creates Amharic session

[ ] current_language set to Amharic

---

## Arabic Session

[ ] Arabic wake word creates Arabic session

[ ] current_language set to Arabic

---

## Context Persistence

[ ] Language context persists through conversation

[ ] Language context survives playback

[ ] Language context survives interruptions

---

## Context Cleanup

[ ] Context cleared after timeout

[ ] Context reset correctly

---

# SECTION 9

# Whisper Tests

## Loading

[ ] Whisper loads successfully

[ ] Whisper loads once only

[ ] Cached model reused

---

## Speech Recognition

[ ] English speech recognized

[ ] Amharic speech recognized

[ ] Arabic speech recognized

---

# SECTION 10

# Scenario Matching Tests

## Scenario Loading

[ ] dialog_config.json loads at startup

[ ] English scenarios cached into english_lookup

[ ] Amharic scenarios cached into amharic_lookup

[ ] Arabic scenarios cached into arabic_lookup

[ ] Invalid scenario entries logged and skipped

---

## Text Normalization

[ ] Input converted to lowercase

[ ] Punctuation removed

[ ] Duplicate spaces collapsed

[ ] Leading/trailing whitespace trimmed

---

## Matching

[ ] Exact match selects correct scenario

[ ] Keyword match selects correct scenario when exact match fails

[ ] Only the active language's lookup is searched

[ ] No matching scenario triggers fallback

---

## Fallback

[ ] unknown_question.wav plays when no scenario matches

[ ] FALLBACK_SCENARIO_SELECTED event generated

[ ] SCENARIO_NOT_FOUND event generated before fallback

---

# SECTION 11

# Audio Playback Tests

## Playback Control

[ ] play_audio() starts playback

[ ] pause_audio() pauses playback

[ ] resume_audio() resumes playback

[ ] Playback position tracked accurately

---

## Format Support

[ ] WAV playback works

[ ] MP3 playback works

---

## Playback Events

[ ] PLAYBACK_STARTED generated on start

[ ] PLAYBACK_FINISHED generated on completion

[ ] Correct audio file selected per scenario match

---

# SECTION 12

# VAD & Interruption Tests

## Interruption Detection

[ ] Speech during playback detected by VAD

[ ] INTERRUPTION_DETECTED event generated

[ ] Playback pauses on interruption

[ ] please_wait.wav plays during interruption

---

## Resume After Interruption

[ ] Silence detected after interruption

[ ] INTERRUPTION_CLEARED event generated

[ ] Original response resumes from stored position

[ ] Original response does not restart from the beginning

---

# SECTION 13

# Timeout Tests

## Conversation Timeout

[ ] TIMEOUT_OCCURRED generated after 30 seconds of inactivity

[ ] Conversation context cleared on timeout

[ ] Language context cleared on timeout

[ ] FSM transitions to FACE_LOST_CHECK then WAITING_FOR_WAKE_WORD when users remain visible

---

# SECTION 14

# Face Persistence & Face Lost Tests

## Persistence

[ ] last_seen updates continuously while a user is visible

[ ] last_seen stops updating once a user disappears

---

## Partial Face Loss

[ ] FACE_LOST generated for a user who leaves the frame

[ ] Active user list updates to remove only the lost user

[ ] Robot remains in WAITING_FOR_WAKE_WORD when at least one recognized user remains visible

[ ] No duplicate greeting occurs for users who remain visible

---

## Complete Face Loss

[ ] ALL_USERS_LOST generated when no recognized users remain

[ ] FSM transitions FACE_LOST_CHECK → RETURN_TO_IDLE → IDLE

[ ] No manual intervention required to reach IDLE

---

# SECTION 15

# Return To Idle & Re-Entry Tests

## Return To Idle

[ ] Active users cleared on RETURN_TO_IDLE

[ ] Language context reset on RETURN_TO_IDLE

[ ] Playback state reset on RETURN_TO_IDLE

[ ] IDLE_ENTERED event generated

---

## Re-Entry

[ ] Recognition resumes correctly after returning to IDLE

[ ] Greeting workflow restarts when a recognized user reappears

[ ] System behaves consistently across repeated IDLE cycles

---

# SECTION 16

# Raspberry Pi Performance Tests

## Resource Usage

[ ] Application runs on Raspberry Pi 4 (8GB RAM)

[ ] Camera runs at 640x480

[ ] Recognition runs every 10th frame, detection every frame

[ ] Whisper base model used

[ ] Memory usage remains stable during extended runtime (no unbounded growth)

[ ] Only latest_frame and latest_audio_chunk retained (no frame/audio history buffers)

---

## Responsiveness

[ ] Wake word detection responds within an acceptable delay on Pi hardware

[ ] Scenario matching responds within an acceptable delay on Pi hardware

[ ] Playback starts without noticeable lag on Pi hardware

---

# SECTION 17

# End-To-End Demonstration Tests

Reference:

DEMO_SCRIPT.md

## Full Workflow

[ ] Complete demonstration workflow (Steps 1-20 of DEMO_SCRIPT.md) succeeds without application restart

[ ] Complete demonstration workflow succeeds without manual intervention

[ ] Complete demonstration workflow succeeds without service crashes

[ ] Complete demonstration workflow succeeds without missing audio

[ ] Complete demonstration workflow succeeds without failed state transitions

[ ] Complete demonstration workflow succeeds without failed language sessions

[ ] Demonstration runs entirely offline (no network access during execution)
