import whisper
from functools import lru_cache

# =====================================================
# Whisper Model
# =====================================================

@lru_cache(maxsize=5)
def load_model(
    size="medium"
):
    """
    Load Whisper model.
    Cached locally.
    """

    model = whisper.load_model(
        size
    )

    return model


# =====================================================
# Transcription
# =====================================================

def transcribe_audio(
    audio_path,
    model
):
    """
    Speech -> Text
    """

    result = model.transcribe(
        audio_path
    )

    return result["text"]


# =====================================================
# Wake Word Detection
# =====================================================

def detect_wake_word(
    transcription,
    wake_words
):
    """
    Returns matched wake word.
    """

    text = transcription.lower()

    for wake_word in wake_words:

        if wake_word.lower() in text:
            return wake_word

    return None