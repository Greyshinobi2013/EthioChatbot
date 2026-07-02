import queue
import numpy as np


class AudioBuffer:
    """
    Thread-safe audio buffer for WebRTC audio frames.
    """

    def __init__(self):
        self.q = queue.Queue()

    def add_audio(self, frame):
        audio = frame.to_ndarray().flatten().astype(np.float32)
        self.q.put(audio)

    def get_audio_chunk(self):

        chunks = []

        while not self.q.empty():
            chunks.append(self.q.get())

        if not chunks:
            return None

        return np.concatenate(chunks)