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
