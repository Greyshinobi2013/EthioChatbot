import pygame
import pyttsx3

# =====================================================
# Audio Engine
# =====================================================

pygame.mixer.init()

tts_engine = pyttsx3.init()

current_file = None

# =====================================================
# Play Audio
# =====================================================

def play_audio(
    file_path
):
    global current_file

    current_file = file_path

    pygame.mixer.music.load(
        file_path
    )

    pygame.mixer.music.play()


# =====================================================
# Pause
# =====================================================

def pause_audio():
    pygame.mixer.music.pause()


# =====================================================
# Resume
# =====================================================

def resume_audio():
    pygame.mixer.music.unpause()


# =====================================================
# Restart
# =====================================================

def restart_audio(
    file_path=None
):
    global current_file

    if file_path:
        current_file = file_path

    if current_file is None:
        return

    pygame.mixer.music.stop()

    pygame.mixer.music.load(
        current_file
    )

    pygame.mixer.music.play()


# =====================================================
# Notification
# =====================================================

def notify_user(
    message="please wait"
):
    """
    Polite voice notification.
    """

    tts_engine.say(
        message
    )

    tts_engine.runAndWait()