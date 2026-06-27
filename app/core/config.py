"""
Central configuration and path resolution for the offline chatbot.

Every other module imports BASE_DIR / file paths from here so that the
project can be relocated or packaged without hunting down hard-coded
strings in five different files.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

APP_DIR = Path(__file__).resolve().parent.parent          # .../app
PROJECT_ROOT = APP_DIR.parent                              # repo root

ASSETS_DIR = APP_DIR / "assets"
AUDIO_DIR = ASSETS_DIR / "audio"
DATA_DIR = APP_DIR / "data"
ENROLLED_FACES_DIR = APP_DIR / "enrolled_faces"

DIALOG_CONFIG_PATH = DATA_DIR / "dialog_config.json"
FACE_DB_PATH = ENROLLED_FACES_DIR / "face_db.pkl"
USERS_META_PATH = ENROLLED_FACES_DIR / "users.json"

for _dir in (ASSETS_DIR, AUDIO_DIR, DATA_DIR, ENROLLED_FACES_DIR):
    _dir.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger with a consistent format.

    Centralising this means every module's log lines are easy to grep
    and we avoid each file reinventing logging.basicConfig (which, if
    called more than once, silently no-ops in the standard library).
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ---------------------------------------------------------------------------
# Runtime-tunable settings
# ---------------------------------------------------------------------------

@dataclass
class Settings:
    """Knobs that affect recognition/VAD behaviour.

    Kept as a plain dataclass (not pulled from env/json) because these
    are the values a developer is most likely to want to tweak directly
    in code while testing on their own webcam/mic, and Streamlit's
    session_state can override per-session as needed.
    """

    # --- Face recognition ---
    face_match_tolerance: float = 0.5      # lower = stricter match (dlib distance)
    face_detect_every_n_frames: int = 5    # skip frames for perf
    face_min_detections_to_confirm: int = 3

    # --- Speech / wake word ---
    whisper_model_size: str = "base"       # tiny/base/small/medium
    sample_rate: int = 16000
    wake_word_listen_seconds: float = 3.0

    # --- VAD / interruption ---
    vad_aggressiveness: int = 2            # 0-3, webrtcvad style
    vad_frame_ms: int = 30
    interruption_rms_threshold: float = 0.02   # fallback energy-based VAD
    interruption_confirm_frames: int = 3        # consecutive voiced frames needed

    # --- Audio ---
    audio_resume_mode: str = "restart"     # "restart" or "resume"


SETTINGS = Settings()


# ---------------------------------------------------------------------------
# Dialog config loader
# ---------------------------------------------------------------------------

def load_dialog_config(path: Path = DIALOG_CONFIG_PATH) -> dict[str, Any]:
    """Load and minimally validate the dialog scenario JSON.

    Raises a clear error rather than letting a KeyError surface deep
    inside the dialog manager later, since a malformed JSON edit by a
    content author is the most likely failure mode in this system.
    """
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)

    required_top_level = {"languages", "scenarios", "default_scenario"}
    missing = required_top_level - config.keys()
    if missing:
        raise ValueError(f"dialog_config.json missing required keys: {missing}")

    if config["default_scenario"] not in config["scenarios"]:
        raise ValueError(
            f"default_scenario '{config['default_scenario']}' not found in scenarios"
        )

    return config


def resolve_audio_path(relative_path: str) -> Path:
    """Resolve an audio path as written in dialog_config.json (relative
    to app/assets/) into an absolute filesystem path.
    """
    return (ASSETS_DIR / relative_path).resolve()
