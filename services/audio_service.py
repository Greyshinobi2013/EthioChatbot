import os
import wave
import json
import queue
import sys
import sounddevice as sd
from vosk import Model, KaldiRecognizer

class AudioService:
    def __init__(self, model_path="models/vosk-model-en-us-0.22"):
        self.model = Model(model_path)
        self.q = queue.Queue()
        self.samplerate = 16000

    def callback(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def listen_and_transcribe(self, duration=5):
        """
        Listens for a fixed duration and returns transcript.
        """
        rec = KaldiRecognizer(self.model, self.samplerate)
        with sd.RawInputStream(samplerate=self.samplerate, blocksize=8000, 
                               dtype='int16', channels=1, callback=self.callback):
            start_time = os.times().elapsed
            while os.times().elapsed - start_time < duration:
                data = self.q.get()
                if rec.AcceptWaveform(data):
                    pass
            
            result = json.loads(rec.FinalResult())
            return result.get("text", "")

    def play_wav(self, file_path):
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            continue

    def get_language_hint(self, transcript):
        # Wake word detection mapping
        text = transcript.lower()
        if "hello" in text: return "en"
        if "ሰላም" in text: return "am"
        if "akkam" in text: return "om"
        return None
