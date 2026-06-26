import re

RULES = {
    "en": {
        "greeting": (r"\b(hello|hi|hey)\b", "assets/wavs/en_greeting.wav"),
        "time": (r"\b(time|clock)\b", "assets/wavs/en_time.wav"),
        "weather": (r"\b(weather|temperature)\b", "assets/wavs/en_weather.wav"),
    },
    "am": {
        "greeting": (r"(ሰላም|ጤና ይስጥልኝ)", "assets/wavs/am_greeting.wav"),
        "time": (r"(ሰዓት|ስንት ነው)", "assets/wavs/am_time.wav"),
    },
    "om": {
        "greeting": (r"(akkam|nagaa)", "assets/wavs/om_greeting.wav"),
    }
}

class RuleEngine:
    def match(self, text, lang="en"):
        if lang not in RULES:
            lang = "en"
        
        for intent, (pattern, response_wav) in RULES[lang].items():
            if re.search(pattern, text, re.IGNORECASE):
                return intent, response_wav
        
        return "unknown", f"assets/wavs/{lang}_fallback.wav"
