import os

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIALOGS_DIR = os.path.join(BASE_DIR, "dialogs")
KNOWN_FACES_DIR = os.path.join(BASE_DIR, "known_faces")
FACE_DB_PATH = os.path.join(BASE_DIR, "known_faces_db.json")

# Ensure directories exist
os.makedirs(DIALOGS_DIR, exist_ok=True)
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

# Ignite words and corresponding language codes
IGNITE_WORDS = {
    "hello": "en",
    "ሰላም": "am",
    "akkam": "om",
    "مرحبا": "ar"
}

# Supported Languages mapping
LANGUAGES = {
    "en": {
        "name": "English",
        "locale": "en-US",
        "fallback_ignite": "hello",
        "default_response": "I didn't quite catch that. Could you please rephrase or ask for 'help'?"
    },
    "am": {
        "name": "Amharic (አማርኛ)",
        "locale": "am-ET",
        "fallback_ignite": "ሰላም",
        "default_response": "እባክዎን በሌላ አባባል ይናገሩ ወይም 'እርዳታ' ብለው ይጠይቁ።"
    },
    "om": {
        "name": "Oromifa (Afaan Oromoo)",
        "locale": "om-ET", # Note: Google Speech Recognition sometimes uses en-US/am-ET for Ethiopia, custom locale representation.
        "fallback_ignite": "akkam",
        "default_response": "Maal jedhanii? Mee irra deebi'aa ykn 'gargaarsa' jedhaa gaafadhaa."
    },
    "ar": {
        "name": "Arabic (العربية)",
        "locale": "ar-SA",
        "fallback_ignite": "مرحبا",
        "default_response": "عذراً، لم أفهم ذلك تماماً. هل يمكنك إعادة الصياغة أو طلب 'مساعدة'؟"
    }
}

# External API Configuration (EthiopicAI & Nimo Labs placeholders)
# Users can override these using environment variables
ETHIOPIC_AI_API_KEY = os.getenv("ETHIOPIC_AI_API_KEY", "your_ethiopic_ai_api_key_here")
ETHIOPIC_AI_TTS_URL = os.getenv("ETHIOPIC_AI_TTS_URL", "https://api.ethiopic.ai/v1/tts")

NIMO_LABS_API_KEY = os.getenv("NIMO_LABS_API_KEY", "your_nimo_labs_api_key_here")
NIMO_LABS_TTS_URL = os.getenv("NIMO_LABS_TTS_URL", "https://api.nimolabs.com/v1/tts")

# Voice engine configuration
OFFLINE_TTS_RATE = 150  # Words per minute
OFFLINE_TTS_VOLUME = 1.0
