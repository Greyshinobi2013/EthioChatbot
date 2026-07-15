# Scenario Matching Rules

This project is NOT an LLM chatbot.

The robot never generates responses.

The robot never generates speech.

Every response comes from a prerecorded audio file.

---

## Conversation Flow

User Speech

↓

Whisper Transcription

↓

Normalize Text

↓

Match Scenario

↓

Locate Response Audio

↓

Play Audio

---

## Text Normalization

Convert to lowercase.

Remove punctuation.

Trim whitespace.

Normalize repeated spaces.

---

## Scenario Structure

{
    "user_text": "",
    "response_audio": ""
}

---

## Example

{
    "user_text": "what is your name",
    "response_audio": "name.wav"
}

---

## Matching Rules

Exact match preferred.

Keyword matching allowed.

Best keyword score wins.

No semantic matching.

No embeddings.

No vector databases.

No generative AI.

---

## Unsupported Queries

If no scenario exists:

Play:

unknown_question.wav

Never generate a custom response.