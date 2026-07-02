from enum import Enum, auto


class BotState(Enum):
    """
    Represents the explicit, deterministic states of the chatbot state machine.
    """

    IDLE = auto()                     # Waiting for recognized face
    ENROLLING = auto()                # User registration in progress
    FACE_DETECTED = auto()            # Face confirmed through consecutive frames
    GREETING = auto()                 # Playing greeting audio
    LISTENING_WAKE_WORD = auto()      # Waiting for wake word
    PLAYING_SCENARIO = auto()         # Playing scenario audio clips
    INTERRUPTED = auto()              # User interrupted playback
    ERROR = auto()                    # System error state