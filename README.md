# EthioChatbot 🤖
An advanced, offline-capable, rule-based multilingual chatbot utilizing computer vision (facial recognition) and speech interface (Speech-to-Text and Text-to-Speech) built with Python and Streamlit.

EthioChatbot seamlessly integrates:
1. **Facial AI**: OpenCV face detection with `face_recognition` (dlib-based embeddings) to identify known users.
2. **Multilingual Ignite Words**: Instantly switches language mode based on keywords ("Hello", "ሰላም", "Akkam", "مرحبا").
3. **Speech Layer**: Multilingual Speech-to-Text via `SpeechRecognition` and Text-to-Speech (offline via `pyttsx3` for English & Arabic, plus integration hooks for `EthiopicAI` & `Nimo Labs` for Amharic & Oromifa voices).
4. **Rich GUI**: Interactive Streamlit dashboard showing real-time camera feeds, detected overlays, active language settings, and chat history.

---

## 📂 Project Architecture

```directory
Ethiochatbot/
├── config.py              # Configuration constants, paths, locales, and API endpoints
├── face_module.py         # OpenCV + face_recognition wrapper, face database persistence
├── dialog_module.py       # Rule-based dialouge processing and dynamic language switching
├── speech_module.py       # Speech-to-Text (STT) and offline/online Text-to-Speech (TTS)
├── app.py                 # Core Streamlit application (UI coordinates and feeds)
├── requirements.txt       # Python dependency package list
├── known_faces_db.json    # Serialized JSON database containing registered face embeddings
├── dialogs/               # Predefined JSON rules per language
│   ├── en.json            # English dialog rules
│   ├── am.json            # Amharic dialog rules
│   ├── om.json            # Oromifa dialog rules
│   └── ar.json            # Arabic dialog rules
└── known_faces/           # Storage directory for captured facial images (.jpg)
```

---

## 🛠️ Setup Instructions

### 1. Prerequisites (System-level Packages)

Because libraries like `face-recognition` require compiling `dlib` (C++ code) and `SpeechRecognition` requires microphone access (`PyAudio`), you must install system-level developer tools before pip installation:

#### Debian / Ubuntu / Linux Mint
```bash
sudo apt update
# System tools for face-recognition / dlib compilation
sudo apt install build-essential cmake g++ -y
# System audio libraries for microphone capturing (PyAudio)
sudo apt install portaudio19-dev python3-dev -y
# Offline TTS output support (espeak)
sudo apt install espeak -y
```

#### macOS (using Homebrew)
```bash
brew install cmake portaudio espeak
```

---

### 2. Python Environment & Installation

1. **Clone or navigate into the workspace:**
   ```bash
   cd /home/tech_shinobi/Documents/Ethiochatbot
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install the dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 🚀 Execution Instructions

Launch the interactive chatbot dashboard using Streamlit:

```bash
streamlit run app.py
```

This starts a local server (typically at `http://localhost:8501`) and automatically opens it in your web browser.

---

## 🌟 How to Use & Test All Features

### 1. Register Your Face
1. In the sidebar, scroll down to the **Face Registration** panel.
2. Enter your name (e.g., `Johannes`) into the name input.
3. Align your face nicely with the camera and click **Capture & Register Face**.
4. The system will grab a frame, extract your facial coordinates, compute the 128-dimensional dlib embedding, save your image to `known_faces/`, and store your embedding in `known_faces_db.json`.

### 2. Real-time Face Recognition & Automatic Greetings
1. Check the box **"Enable Real-time Webcam Feed"** on the main panel.
2. Once the feed turns on, look into the camera.
3. If an "Unknown" face is detected, a red bounding box appears.
4. If a registered face (e.g., `Johannes`) is detected, a green bounding box with their name appears.
5. The chatbot will **automatically recognize** the user, add a greeting to the chat history, and speak the greeting aloud!
   - *Example (English)*: *"Hello Johannes, how can I help you today?"*

### 3. Ignite Words for Language Switching
The chatbot is constantly watching for language ignite words. Try typing or speaking:
* Type/Speak `"Hello"` or `"hello computer"` → Active language switches to **English**!
* Type/Speak `"ሰላም"` or `"ሰላም ቻትቦት"` → Active language switches to **Amharic (አማርኛ)**!
* Type/Speak `"Akkam"` or `"akkam gari"` → Active language switches to **Oromifa (Afaan Oromoo)**!
* Type/Speak `"مرحبا"` or `"مرحبا بك"` → Active language switches to **Arabic (العربية)**!

*The UI will instantly update its language mode status indicators and respond in the newly activated language!*

### 4. Rule-Based Conversation Matcher
For each language, queries are matched against keys inside `dialogs/*.json`. Try asking these in your active language:
* **English**: `"how are you"`, `"name"`, `"help"`, `"thanks"`, `"bye"`
* **Amharic**: `"እንዴት ነህ"`, `"ስምህ ማን ነው"`, `"እርዳታ"`, `"አመሰግናለሁ"`, `"ደህና ሁን"`
* **Oromifa**: `"akkam jirta"`, `"maqaan kee eenyu"`, `"gargaarsa"`, `"galatoomi"`, `"nagaatti"`
* **Arabic**: `"كيف حالك"`, `"ما اسمك"`, `"مساعدة"`, `"شكرا"`, `"مع السلامة"`

### 5. Multilingual Speech Interface (STT and TTS)
* **STT**: Click **🎙️ Voice Input (Listen)**. Speak a phrase (e.g., *"How are you"* or Amharic *"እንዴት ነህ"* if Amharic mode is selected). The chatbot captures your speech using the microphone, transcribes it through the Google API using the correct language-locale, processes it through the rules engine, and responds!
* **TTS (Natural Voices)**: English, Amharic, and Arabic responses are spoken using free, natural-sounding neural voices via `edge-tts` (Microsoft's online TTS service — no API key required, just an internet connection). This replaces the robotic offline voice for these three languages whenever you're online.
* **TTS (Offline Fallback)**: If there's no internet connection (or `edge-tts` isn't installed), English and Arabic automatically fall back to the offline robotic voice via `pyttsx3`.
* **TTS (Online API Integration for Oromifa)**:
  - `edge-tts` doesn't currently offer an Oromifa voice, so Oromifa keeps using the `Nimo Labs` API hook for natural speech.
  - To hook up a real key, set it as an environment variable:
    ```bash
    export NIMO_LABS_API_KEY="your-real-key"
    ```
  - You can also still set `ETHIOPIC_AI_API_KEY` as an alternate/backup Amharic voice provider, though `edge-tts` will be tried first.
  - When an online provider is active, the chatbot automatically sends a POST request, downloads the synthesized `.mp3` voice, plays it locally, and generates a neat, interactive play audio widget inside the chat window so you can play it directly inside your browser!

---

## 📝 Editing Dialog Rules

You can customize the conversation at any time by editing the JSON files in the `dialogs/` folder:
* Keys should be in **lowercase**.
* When a user inputs text, the chatbot checks if any of your JSON keys are present in their query, and replies with the matched value.
* If multiple keywords are present, it matches the longest keyword first to ensure specificity.
