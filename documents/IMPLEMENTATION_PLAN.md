# EthioChatbot V2 Implementation Plan

## Purpose

This document defines the implementation roadmap for EthioChatbot V2.

The objective is to deliver a fully working, end-to-end demonstratable robot within approximately five hours of development effort.

The implementation strategy prioritizes:

1. End-to-end functionality
2. Demonstration readiness
3. Raspberry Pi compatibility
4. Stability
5. Maintainability

The implementation plan is intentionally milestone-driven.

Each milestone must be completed, verified, and integrated before proceeding.

---

# Development Strategy

EthioChatbot V2 will be built incrementally.

Principles:

- Build
- Verify
- Integrate
- Continue

Avoid:

- Building everything at once
- Creating untested modules
- Skipping integration steps

Every milestone must end in a runnable state.

---

# Milestone 1

# Foundation & Project Bootstrap

## Goal

Create the application foundation.

## Deliverables

requirements.txt

app.py

logger.py

state_manager.py

config loader

service bootstrap framework

application startup workflow

---

## Tasks

Create:

- project startup sequence
- configuration loader
- centralized logging
- shared state management
- service registration system

Implement:

SYSTEM_STARTUP workflow

SYSTEM_SHUTDOWN workflow

---

## Verification

✓ Application starts

✓ Configuration loads

✓ Logging works

✓ Shared state initializes

✓ Services register successfully

---

## Completion Criteria

Project starts without errors.

---

# Milestone 2

# Event Bus & State Machine

## Goal

Implement the control backbone.

## Deliverables

event_bus.py

Finite State Machine

event subscriptions

state transitions

---

## Tasks

Implement:

Event publishing

Event subscription

Event dispatch

FSM transition validation

State logging

State ownership

States:

- IDLE
- FACE_DETECTED
- FACE_RECOGNIZED
- PRIORITY_SORTING
- GREETING
- WAITING_FOR_WAKE_WORD
- CONVERSATION_ACTIVE
- PLAYING_AUDIO
- INTERRUPTED
- TIMEOUT
- FACE_LOST_CHECK
- RETURN_TO_IDLE

---

## Verification

✓ Events published

✓ Events received

✓ State transitions work

✓ Invalid transitions rejected

✓ Transitions logged

---

## Completion Criteria

FSM controls robot behavior successfully.

---

# Milestone 3

# Face Enrollment System

## Goal

Create user enrollment functionality.

## Deliverables

Enrollment Page

Face Storage

User Metadata Storage

Embedding Storage

---

## Tasks

Implement:

Webcam enrollment

Image upload

User ID entry

Priority assignment

Preferred language selection

Face storage

Embedding generation

Metadata storage

Store:

- user_id
- priority
- preferred_language
- image_path
- embedding_path

---

## Verification

✓ Enrollment works

✓ Image stored

✓ Embedding stored

✓ Metadata stored

✓ User appears in list

---

## Completion Criteria

User enrollment fully functional.

---

# Milestone 4

# Face Detection & Recognition

## Goal

Recognize one or more enrolled users.

## Deliverables

camera_service.py

face_recognition.py

face tracking

face persistence

---

## Tasks

Implement:

Camera initialization

Face detection

Face recognition

Multi-face support

Face tracking

last_seen tracking

FACE_LOST detection

Recognition interval optimization

Recommendations:

Detect every frame

Recognize every 10th frame

---

## Verification

✓ Faces detected

✓ Users recognized

✓ Multiple users supported

✓ last_seen updates

✓ FACE_LOST works

---

## Completion Criteria

Recognition system fully operational.

---

# Milestone 5

# Priority Greeting System

## Goal

Implement sequential priority-based greetings.

## Deliverables

Priority sorting

Greeting queue

Greeting playback

---

## Tasks

Implement:

Priority sorting

Greeting queue creation

Sequential greeting playback

Personalized greeting support

Fallback greeting support

Workflow:

Recognize Users

↓

Sort By Priority

↓

Greeting Queue

↓

Sequential Playback

↓

WAITING_FOR_WAKE_WORD

---

## Verification

✓ Users sorted correctly

✓ Greetings follow priority order

✓ English greetings used

✓ WAITING_FOR_WAKE_WORD entered

---

## Completion Criteria

Greeting workflow complete.

---

# Milestone 6

# Whisper & Wake Word System

## Goal

Implement multilingual wake-word detection.

## Deliverables

whisper_utils.py

wake word detection

language context system

---

## Tasks

Load Whisper once

Use model:

base

Implement:

English wake words

Amharic wake words

Arabic wake words

Language detection from wake word

Language context cache

Store:

current_language

---

## Verification

✓ Whisper loads

✓ English wake words work

✓ Amharic wake words work

✓ Arabic wake words work

✓ Language context stored

---

## Completion Criteria

Conversation activation works.

---

# Milestone 7

# Scenario Matching Engine

## Goal

Implement deterministic conversations.

## Deliverables

Scenario loader

Scenario cache

Matching engine

Language aware lookup

---

## Tasks

Load:

dialog_config.json

Normalize text

Match scenarios

Select response audio

Fallback response

Create:

english_lookup

amharic_lookup

arabic_lookup

---

## Verification

✓ Scenario loading works

✓ Exact matching works

✓ Keyword matching works

✓ Fallback works

---

## Completion Criteria

Scenario engine complete.

---

# Milestone 8

# Audio Playback System

## Goal

Implement response playback.

## Deliverables

playback.py

Position tracking

Playback control

---

## Tasks

Implement:

play_audio()

pause_audio()

resume_audio()

restart_audio()

Track:

Current file

Current position

Playback state

Support:

WAV

MP3

---

## Verification

✓ Audio plays

✓ Playback position stored

✓ Resume works

✓ State updates work

---

## Completion Criteria

Playback engine complete.

---

# Milestone 9

# VAD & Interruption Handling

## Goal

Handle user interruptions.

## Deliverables

vad_handler.py

Interruption workflow

Resume workflow

---

## Tasks

Implement:

Speech detection

Silence detection

Interrupt playback

Play interruption audio

Resume playback

Workflow:

Response Playing

↓

User Speaks

↓

Pause Response

↓

Play please_wait.wav

↓

Wait For Silence

↓

Resume Response

---

## Verification

✓ Interruption detected

✓ Playback pauses

✓ Interruption audio plays

✓ Playback resumes

✓ Playback resumes at correct position

---

## Completion Criteria

Interruption workflow complete.

---

# Milestone 10

# Conversation Manager

## Goal

Implement complete conversation lifecycle.

## Deliverables

conversation_manager.py

Timeout handling

Language context

Conversation orchestration

---

## Tasks

Implement:

Session management

Language persistence

Timeout management

Conversation cleanup

Workflow:

Wake Word

↓

Conversation

↓

Playback

↓

Timeout

↓

WAITING_FOR_WAKE_WORD

---

## Verification

✓ Conversations work

✓ Context persists

✓ Timeout works

✓ Context clears

---

## Completion Criteria

Conversation workflow complete.

---

# Milestone 11

# Dashboard & Administration

## Goal

Create monitoring and administration pages.

## Deliverables

Dashboard

Enrollment page

Scenario page

Settings page

---

## Tasks

Dashboard:

- camera feed
- active users
- language
- current state
- logs

Enrollment:

- add users

Scenario Management:

- add scenarios
- edit scenarios
- delete scenarios

Settings:

- camera settings
- whisper settings
- timeout settings

---

## Verification

✓ Dashboard works

✓ Enrollment works

✓ Scenario management works

✓ Settings work

---

## Completion Criteria

Administration interface complete.

---

# Milestone 12

# Raspberry Pi Optimization

## Goal

Optimize for Raspberry Pi 4 (8GB).

## Tasks

Configure:

640x480 camera

Recognition interval:

10 frames

Whisper model:

base

Scenario caching

Embedding caching

Language caching

Limit memory usage

Keep:

latest_frame

latest_audio_chunk

only.

---

## Verification

✓ Memory usage acceptable

✓ CPU usage acceptable

✓ No unnecessary allocations

---

## Completion Criteria

Application ready for Raspberry Pi deployment.

---

# Milestone 13

# End-To-End Integration

## Goal

Integrate all modules.

---

## Full Workflow

System Startup

↓

Face Recognition

↓

Priority Sorting

↓

Sequential Greetings

↓

WAITING_FOR_WAKE_WORD

↓

Wake Word

↓

Conversation

↓

Scenario Match

↓

Audio Playback

↓

Interruption

↓

Resume

↓

Timeout

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

## Verification

Run:

DEMO_SCRIPT.md

Run:

ACCEPTANCE_TESTS.md

Fix all failures.

---

## Completion Criteria

All modules integrated successfully.

---

# Final Release Validation

The project is release-ready only when:

✓ All milestones completed

✓ All acceptance tests pass

✓ Demo script succeeds

✓ No TODO comments remain

✓ No placeholder code remains

✓ No mock implementations remain

✓ Raspberry Pi profile satisfied

✓ Complete workflow operational

---

# Project Completion Definition

EthioChatbot V2 is complete only when a user can:

✓ Be recognized

✓ Be prioritized

✓ Be greeted

✓ Activate conversation using wake words

✓ Speak English

✓ Speak Amharic

✓ Speak Arabic

✓ Receive prerecorded responses

✓ Interrupt responses

✓ Resume responses

✓ Timeout correctly

✓ Remain in WAITING_FOR_WAKE_WORD while visible

✓ Cause IDLE transition when leaving

✓ Successfully complete the demonstration workflow

The final deliverable must be a fully offline, Raspberry Pi optimized, multilingual conversational robot ready for demonstration.
