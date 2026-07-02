import logging
import sys
from pathlib import Path

# ── Project Paths ─────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent.parent

CORE_DIR = ROOT_DIR / "core"
SCENARIO_DIR = ROOT_DIR / "scenarios"

AUDIO_DIR = ROOT_DIR / "audio"
CLIPS_DIR = AUDIO_DIR / "clips"

FACES_DIR = ROOT_DIR / "faces"
ENROLLED_DIR = FACES_DIR / "enrolled"

MODELS_DIR = ROOT_DIR / "models"
UTILS_DIR = ROOT_DIR / "utils"

# ── Ensure Required Directories Exist ────────────────────────────────

for directory in [
    SCENARIO_DIR,
    AUDIO_DIR,
    CLIPS_DIR,
    FACES_DIR,
    ENROLLED_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)

# ── Hardware & Model Defaults ────────────────────────────────────────

WHISPER_MODEL_SIZE = "medium"
VAD_AGGRESSIVENESS = 2
FACE_CONFIRMATION_FRAMES = 5
DEFAULT_CAMERA_INDEX = 0

# ── Logging Configuration ────────────────────────────────────────────

def setup_logging(level=logging.INFO):
    """
    Configures standardized logging for the application.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    return logging.getLogger("Ethiobot")


logger = setup_logging()