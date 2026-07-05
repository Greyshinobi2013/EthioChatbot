import webrtcvad
import sounddevice as sd
import numpy as np
import threading

# =====================================================
# Globals
# =====================================================

vad = None
running = False

SAMPLE_RATE = 16000
FRAME_DURATION = 30

# =====================================================
# Initialize VAD
# =====================================================

def start_vad(
    aggressiveness=2
):
    global vad

    vad = webrtcvad.Vad(
        aggressiveness
    )


# =====================================================
# Speech Detection
# =====================================================

def is_speech(audio_chunk):
    """
    audio_chunk must be raw bytes.
    """

    if vad is None:
        start_vad()

    return vad.is_speech(
        audio_chunk,
        SAMPLE_RATE
    )


# =====================================================
# Interruption Monitoring
# =====================================================

def monitor_interruptions(
    callback=None
):
    """
    Listen for interruptions.
    """

    global running

    running = True

    def _worker():

        while running:

            audio = sd.rec(
                int(
                    SAMPLE_RATE *
                    FRAME_DURATION /
                    1000
                ),
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16"
            )

            sd.wait()

            chunk = (
                audio
                .flatten()
                .tobytes()
            )

            if is_speech(chunk):

                if callback:
                    callback()

    thread = threading.Thread(
        target=_worker,
        daemon=True
    )

    thread.start()


def stop_monitoring():

    global running
    running = False