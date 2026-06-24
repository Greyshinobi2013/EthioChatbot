import os
import json
import logging
import config

logger = logging.getLogger("DialogModule")

class DialogManager:
    def __init__(self):
        self.active_lang = "en"  # Default active language is English
        self.dialogs = {}
        self.load_dialogs()

    def load_dialogs(self):
        """Loads dialog JSON files for all supported languages."""
        for lang_code, lang_info in config.LANGUAGES.items():
            file_path = os.path.join(config.DIALOGS_DIR, f"{lang_code}.json")
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.dialogs[lang_code] = json.load(f)
                    logger.info(f"Loaded dialog rules for {lang_info['name']} ({lang_code}) from {file_path}")
                except Exception as e:
                    logger.error(f"Error loading dialog file for {lang_code}: {e}")
                    self.dialogs[lang_code] = {}
            else:
                logger.warning(f"Dialog file {file_path} not found. Creating placeholder.")
                # Write a default placeholder
                placeholder_data = {lang_info["fallback_ignite"]: f"Greeting in {lang_info['name']}"}
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(placeholder_data, f, indent=2, ensure_ascii=False)
                    self.dialogs[lang_code] = placeholder_data
                except Exception as ex:
                    logger.error(f"Failed to create placeholder dialog for {lang_code}: {ex}")
                    self.dialogs[lang_code] = {}

    def check_for_ignite_word(self, text):
        """Checks if the user input contains one of the four language ignite words.
        
        Args:
            text (str): The raw input string from the user.
            
        Returns:
            str or None: The language code (e.g., 'en', 'am') if found, otherwise None.
        """
        if not text:
            return None

        cleaned_text = text.strip().lower()
        
        # Check each ignite word in the input text
        for ignite_word, lang_code in config.IGNITE_WORDS.items():
            # Check for substring match (e.g. if user says "Hello robot" or "ሰላም ቻትቦት")
            # We also handle Ethiopic script correctly by comparing UTF-8 values
            if ignite_word.lower() in cleaned_text:
                return lang_code
                
        return None

    def switch_language(self, lang_code):
        """Switches the active language mode.
        
        Args:
            lang_code (str): The destination language code.
            
        Returns:
            str: Greeting/Confirmation of language switch.
        """
        if lang_code in config.LANGUAGES:
            prev_lang = self.active_lang
            self.active_lang = lang_code
            lang_name = config.LANGUAGES[lang_code]["name"]
            logger.info(f"Language switched from '{prev_lang}' to '{lang_code}' ({lang_name})")
            
            # Retrieve the greeting/ignite response as confirmation
            ignite_word = config.LANGUAGES[lang_code]["fallback_ignite"]
            confirmation = self.dialogs.get(lang_code, {}).get(ignite_word, f"Language switched to {lang_name}.")
            return confirmation
        else:
            logger.warning(f"Attempted to switch to unsupported language: {lang_code}")
            return f"Language {lang_code} is not supported."

    def respond(self, text):
        """Processes user input, detects language switching ignite words, matches keywords
        against predefined rules, and returns the appropriate scripted output.
        
        Args:
            text (str): User input string.
            
        Returns:
            dict: A response dictionary containing:
                  'response': string of the reply
                  'lang_switched': boolean indicating if a switch occurred
                  'active_lang': string code of the current language
        """
        if not text or text.strip() == "":
            return {
                "response": "",
                "lang_switched": False,
                "active_lang": self.active_lang
            }

        # 1. Check for ignite words (language switching)
        detected_lang = self.check_for_ignite_word(text)
        lang_switched = False
        
        if detected_lang and detected_lang != self.active_lang:
            response_text = self.switch_language(detected_lang)
            lang_switched = True
            return {
                "response": response_text,
                "lang_switched": lang_switched,
                "active_lang": self.active_lang
            }

        # 2. Key-based dialog rule matching for current active language
        cleaned_input = text.strip().lower()
        current_rules = self.dialogs.get(self.active_lang, {})
        
        matched_response = None
        
        # We search for keywords in the user's text.
        # To match the longest/most specific keywords first, we sort the rules by key length descending.
        sorted_keywords = sorted(current_rules.keys(), key=len, reverse=True)
        
        for keyword in sorted_keywords:
            if keyword.lower() in cleaned_input:
                matched_response = current_rules[keyword]
                break

        # 3. Fallback if no matching rule is found
        if matched_response is None:
            matched_response = config.LANGUAGES[self.active_lang]["default_response"]
            
        return {
            "response": matched_response,
            "lang_switched": lang_switched,
            "active_lang": self.active_lang
        }
