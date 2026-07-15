# Architecture

## Overview

The Offline Multimodal Conversational Robot is a fully offline, event-driven, server-side processing system.

All AI processing executes on the backend.

Streamlit is used only for monitoring, administration, and configuration.

The robot continuously processes:

- Live webcam feed
- Live microphone feed

without requiring user interaction.

---

## Architectural Layers

### Presentation Layer

Components:

- Streamlit Dashboard
- Face Enrollment Page
- Scenario Management Page
- Settings Page

Responsibilities:

- Display information
- Show logs
- Show status
- Manage settings
- Manage scenarios

Restrictions:

- No computer vision logic
- No speech recognition logic
- No conversation logic
- No audio playback logic

---

### Service Layer

Services:

- Camera Service
- Face Recognition Service
- Whisper Service
- VAD Service
- Playback Service
- Conversation Service

Responsibilities:

- Handle business logic
- Publish events
- Consume events

---

### Core Layer

Modules:

- Event Bus
- State Machine
- Domain Models

Responsibilities:

- Manage workflow
- Manage state transitions

---

### Persistence Layer

Storage:

- Face Database
- Dialog Database
- Settings Database

Format:

- JSON
- Local Files

---

## Real Time Media Pipeline

Camera

↓

Face Detection

↓

Face Recognition

↓

State Event

Microphone

↓

Wake Word Detection

↓

Whisper

↓

Scenario Matching

↓

Audio Playback

---

## Thread Model

Required Threads:

- Camera Thread
- Audio Capture Thread
- VAD Thread
- Playback Thread
- Conversation Thread
- Logging Thread

Services run independently.

Failure of one service must not crash the entire application.

---

## Start Up Sequence

Load Configuration

↓

Initialize Logging

↓

Initialize Camera

↓

Initialize Audio Devices

↓

Load Face Database

↓

Load Whisper Model

↓

Start Service Threads

↓

Initialize State Machine

↓

Enter IDLE State

---

## Shutdown Sequence

Stop Threads

↓

Release Camera

↓

Release Audio Devices

↓

Save State

↓

Exit Cleanly