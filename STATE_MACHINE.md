# State Machine Specification

The robot is controlled using a Finite State Machine.

Every state transition must be logged.

---

## States

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

## Transition Diagram

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

---

## Rules

State transitions occur only through events.

Direct state manipulation is prohibited.

All transitions must be validated before execution.

Invalid transitions must be logged as warnings.