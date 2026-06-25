import os
import logging
import tempfile
import asyncio
import requests
import config

# Set up logging
logger = logging.getLogger("SpeechModule")

# Try to import SpeechRecognition
try:
    import speech_recognition as sr
    STT_AVAILABLE = True
    logger.info("Successfully imported speech_recognition.")
except ImportError:
    STT_AVAILABLE = False
    logger.warning("Could not import 'speech_recognition'. Speech input will be disabled.")

# Try to import pyttsx3
try:
    import pyttsx3
    TTS_AVAILABLE = True
    logger.info("Successfully imported pyttsx3.")
except ImportError:
    TTS_AVAILABLE = False
    logger.warning("Could not import 'pyttsx3'. Offline TTS will be disabled.")

# Try to import edge-tts (free, natural-sounding neural voices, no API key required)
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
    logger.info("Successfully imported edge_tts. Natural neural voices enabled.")
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning(
        "Could not import 'edge_tts'. Natural-sounding voices will be disabled; "
        "falling back to offline robotic TTS. Run 'pip install edge-tts' to enable."
    )


class STTHandler:
    """Handles Speech-to-Text conversion using SpeechRecognition."""
    def __init__(self):
        self.recognizer = None
        self.microphone = None
        
        if STT_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                # Use default microphone
                self.microphone = sr.Microphone()
                # Adjust for ambient noise on initialization
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
                logger.info("Microphone initialized and ambient noise level adjusted.")
            except Exception as e:
                logger.error(f"Failed to initialize microphone/recognizer: {e}")
                self.recognizer = None
                self.microphone = None

    def listen(self, lang_code="en", timeout=5.0, phrase_time_limit=10.0):
        """Listens to microphone input and converts it to text.
        
        Args:
            lang_code (str): Language code ('en', 'am', 'om', 'ar') to determine STT locale.
            timeout (float): Maximum seconds to wait for speech before timing out.
            phrase_time_limit (float): Maximum seconds to allow a phrase to continue.
            
        Returns:
            str: Transcribed text, or None if transcription failed/timed out.
        """
        if not STT_AVAILABLE or not self.recognizer or not self.microphone:
            logger.warning("STT is unavailable. Cannot listen.")
            return None

        locale = config.LANGUAGES.get(lang_code, {}).get("locale", "en-US")
        logger.info(f"Listening... (Language locale: {locale})")

        try:
            with self.microphone as source:
                # Capture the audio
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                
            logger.info("Audio captured. Transcribing...")
            
            # Use Google Speech Recognition (free tier, online)
            text = self.recognizer.recognize_google(audio, language=locale)
            logger.info(f"Transcribed Text: '{text}'")
            return text

        except sr.WaitTimeoutError:
            logger.info("Listening timed out: No speech detected.")
            return None
        except sr.UnknownValueError:
            logger.warning("Google Speech Recognition could not understand the audio.")
            return None
        except sr.RequestError as e:
            logger.error(f"Could not request results from Google Speech Recognition service; {e}")
            return None
        except Exception as e:
            logger.error(f"Error during speech capturing/transcription: {e}")
            return None


class TTSHandler:
    """Handles Text-to-Speech conversion using pyttsx3 (offline) and API integrations (online)."""
    def __init__(self):
        self.engine = None
        self.temp_dir = tempfile.gettempdir()
        
        if TTS_AVAILABLE:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', config.OFFLINE_TTS_RATE)
                self.engine.setProperty('volume', config.OFFLINE_TTS_VOLUME)
                
                # Setup default voices
                self.voices = self.engine.getProperty('voices')
                logger.info(f"Offline pyttsx3 TTS initialized. Available voices: {len(self.voices)}")
            except Exception as e:
                logger.error(f"Failed to initialize pyttsx3 engine: {e}")
                self.engine = None

    def _get_voice_by_lang(self, lang_code):
        """Attempts to find an appropriate voice on the system for a given language."""
        if not self.voices:
            return None

        # Look for matching language hints in the voice properties
        lang_hints = {
            "en": ["english", "en_us", "en_gb", "en"],
            "ar": ["arabic", "ar_sa", "ar_eg", "ar"]
        }

        hints = lang_hints.get(lang_code, [])
        for voice in self.voices:
            voice_id = voice.id.lower()
            voice_name = voice.name.lower()
            # Check languages attribute if it exists
            if hasattr(voice, 'languages') and voice.languages:
                for lang in voice.languages:
                    if any(hint in lang.lower() for hint in hints):
                        return voice.id
            # Fallback to name/id matching
            if any(hint in voice_id or hint in voice_name for hint in hints):
                return voice.id

        # Return default voice if no specific match
        return self.voices[0].id

    def speak_offline(self, text, lang_code="en"):
        """Speaks text offline using pyttsx3.
        
        Args:
            text (str): Text to speak.
            lang_code (str): Language code.
        """
        if not self.engine:
            logger.warning("Offline TTS engine is not available. Skipping voice synthesis.")
            return

        try:
            # Set appropriate voice if available
            voice_id = self._get_voice_by_lang(lang_code)
            if voice_id:
                self.engine.setProperty('voice', voice_id)
                
            logger.info(f"Speaking offline ({lang_code}): '{text}'")
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            logger.error(f"Error during offline TTS: {e}")

    def _play_audio_file(self, audio_path):
        """Plays an audio file locally using whichever system player is available.

        Args:
            audio_path (str): Path to the audio file (mp3) to play.
        """
        if not audio_path:
            return
        try:
            import subprocess
            if os.name == 'posix':  # Linux/macOS
                for player in ['aplay', 'paplay', 'mpg123', 'cvlc', 'play', 'ffplay']:
                    if subprocess.run(['which', player], capture_output=True).returncode == 0:
                        extra_args = ['-nodisp', '-autoexit'] if player == 'ffplay' else []
                        subprocess.Popen([player, *extra_args, audio_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        break
            elif os.name == 'nt':  # Windows
                os.startfile(audio_path)
        except Exception as e:
            logger.error(f"Error playing audio file locally: {e}")

    def speak_edge_tts(self, text, lang_code):
        """Synthesizes natural-sounding speech using Microsoft Edge's free neural TTS service.

        Args:
            text (str): Text to speak.
            lang_code (str): Language code ('en', 'am', 'ar'). Oromifa ('om') is not
                              currently supported by this service.

        Returns:
            str: Path to the generated MP3 audio file, or None if unavailable/failed.
        """
        if not EDGE_TTS_AVAILABLE:
            return None

        voice = config.EDGE_TTS_VOICES.get(lang_code)
        if not voice:
            logger.info(f"No edge-tts neural voice configured for language '{lang_code}'.")
            return None

        temp_file = os.path.join(self.temp_dir, f"edge_tts_{lang_code}_{hash(text)}.mp3")

        try:
            async def _synthesize():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(temp_file)

            asyncio.run(_synthesize())
            logger.info(f"Synthesized natural '{lang_code}' voice via edge-tts ({voice}) -> {temp_file}")
            return temp_file
        except Exception as e:
            logger.error(f"Edge TTS synthesis failed for '{lang_code}' (check internet connection): {e}")
            return None

    def speak_amharic_api(self, text):
        """Integration hook for EthiopicAI API to generate natural Amharic voices.
        
        Args:
            text (str): Amharic text to speak.
            
        Returns:
            str: Path to the generated audio file, or None if failed.
        """
        logger.info(f"Synthesizing Amharic voice via EthiopicAI API: '{text}'")
        
        # Check if API key is configured
        if "your_ethiopic_ai" in config.ETHIOPIC_AI_API_KEY:
            logger.warning("EthiopicAI API key is using placeholder value. Skipping API request.")
            return None

        headers = {
            "Authorization": f"Bearer {config.ETHIOPIC_AI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "voice": "am-ET-standard", # Example voice ID
            "format": "mp3"
        }

        try:
            response = requests.post(config.ETHIOPIC_AI_TTS_URL, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                # Save audio response to temporary file
                temp_file = os.path.join(self.temp_dir, f"amharic_tts_{hash(text)}.mp3")
                with open(temp_file, "wb") as f:
                    f.write(response.content)
                logger.info(f"Successfully generated Amharic voice at {temp_file}")
                return temp_file
            else:
                logger.error(f"EthiopicAI API returned status code {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Failed to connect to EthiopicAI API: {e}")
            return None

    def speak_oromifa_api(self, text):
        """Integration hook for Nimo Labs API to generate natural Oromifa voices.
        
        Args:
            text (str): Oromifa text to speak.
            
        Returns:
            str: Path to the generated audio file, or None if failed.
        """
        logger.info(f"Synthesizing Oromifa voice via Nimo Labs API: '{text}'")
        
        # Check if API key is configured
        if "your_nimo_labs" in config.NIMO_LABS_API_KEY:
            logger.warning("Nimo Labs API key is using placeholder value. Skipping API request.")
            return None

        headers = {
            "Authorization": f"Bearer {config.NIMO_LABS_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "voice": "om-ET-standard", # Example voice ID
            "format": "mp3"
        }

        try:
            response = requests.post(config.NIMO_LABS_TTS_URL, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                # Save audio response to temporary file
                temp_file = os.path.join(self.temp_dir, f"oromifa_tts_{hash(text)}.mp3")
                with open(temp_file, "wb") as f:
                    f.write(response.content)
                logger.info(f"Successfully generated Oromifa voice at {temp_file}")
                return temp_file
            else:
                logger.error(f"Nimo Labs API returned status code {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Failed to connect to Nimo Labs API: {e}")
            return None

    def speak_output(self, text, lang_code="en", play_local=True):
        """Speaks the response based on the active language.

        Voice priority per language:
          1. edge-tts natural neural voice (en, am, ar) — free, no API key, sounds human.
          2. Online API hooks (EthiopicAI for am, Nimo Labs for om) — used if edge-tts
             is unavailable (e.g. no internet) or for om, which edge-tts doesn't support.
          3. Offline pyttsx3 robotic voice — final fallback so something is always spoken.

        Args:
            text (str): Response text to be spoken.
            lang_code (str): Language code ('en', 'am', 'om', 'ar').
            play_local (bool): Whether to play audio locally on the host machine.

        Returns:
            str: Path to synthesized MP3 audio file if an online voice was used, or None.
        """
        if not text:
            return None

        # 1. Try the natural-sounding neural voice first (en, am, ar)
        if lang_code in config.EDGE_TTS_VOICES:
            audio_path = self.speak_edge_tts(text, lang_code)
            if audio_path:
                if play_local:
                    self._play_audio_file(audio_path)
                return audio_path
            logger.warning(f"Natural voice unavailable for '{lang_code}', falling back.")

        # 2. Online TTS API hooks for Ethiopic languages (also covers 'am' if edge-tts failed)
        if lang_code == "am":
            audio_path = self.speak_amharic_api(text)
            if audio_path:
                if play_local:
                    self._play_audio_file(audio_path)
                return audio_path

        elif lang_code == "om":
            audio_path = self.speak_oromifa_api(text)
            if audio_path:
                if play_local:
                    self._play_audio_file(audio_path)
                return audio_path

        # 3. Final fallback: offline robotic TTS (en/ar handled here too if edge-tts failed)
        if play_local:
            self.speak_offline(text, lang_code)
        return None
