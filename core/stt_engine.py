import whisper
import torch
import numpy as np

from typing import Callable, List, Optional
from core.config import logger, WHISPER_MODEL_SIZE


class STTEngine:

    def __init__(
        self,
        model_size: str = WHISPER_MODEL_SIZE,
        device: Optional[str] = None
    ):

        self.model_size = model_size

        self.device = (
            device
            if device
            else ("cuda" if torch.cuda.is_available() else "cpu")
        )

        self.model = None

        self.on_transcript = None
        self.on_wake_word = None
        self.wake_words: List[str] = []

        self._load_model()

    # ------------------------------------------------------

    def _load_model(self):

        logger.info(
            f"Loading Whisper '{self.model_size}' on {self.device}"
        )

        self.model = whisper.load_model(
            self.model_size,
            device=self.device
        )

        logger.info("Whisper model loaded.")

    # ------------------------------------------------------

    def process_audio(self, audio_data: np.ndarray):

        if audio_data is None or len(audio_data) < 16000:
            return

        try:

            result = self.model.transcribe(
                audio_data,
                fp16=(self.device == "cuda"),
                verbose=False
            )

            text = result["text"].strip()

            if not text:
                return

            logger.info(f"STT: {text}")

            if self.on_transcript:
                self.on_transcript(text)

            lower = text.lower()

            for ww in self.wake_words:
                if ww in lower:

                    logger.info(f"Wake word: {ww}")

                    if self.on_wake_word:
                        self.on_wake_word(ww)

                    break

        except Exception:
            logger.exception("Whisper failed")