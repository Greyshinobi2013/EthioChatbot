import os
import time
import logging
import cv2
import streamlit as st
from PIL import Image

import config
from face_module import FaceHandler, FACE_REC_AVAILABLE
from dialog_module import DialogManager
from speech_module import STTHandler, TTSHandler, STT_AVAILABLE, TTS_AVAILABLE

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("EthioChatbotApp")

# Page Configuration
st.set_page_config(
    page_title="EthioChatbot - Multilingual AI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 2rem;
        text-align: center;
    }
    .status-card {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        border: 1px solid #E5E7EB;
    }
    .chat-container {
        border: 1px solid #E5E7EB;
        border-radius: 0.5rem;
        padding: 1.5rem;
        height: 500px;
        overflow-y: auto;
        background-color: #F9FAFB;
        margin-bottom: 1rem;
    }
    .banner-text {
        font-weight: bold;
        color: #111827;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Stateful Initialization
# -----------------------------------------------------------------------------
if "face_handler" not in st.session_state:
    st.session_state.face_handler = FaceHandler()
if "dialog_manager" not in st.session_state:
    st.session_state.dialog_manager = DialogManager()
if "stt_handler" not in st.session_state:
    st.session_state.stt_handler = STTHandler()
if "tts_handler" not in st.session_state:
    st.session_state.tts_handler = TTSHandler()

# Session state variables
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "recognized_user" not in st.session_state:
    st.session_state.recognized_user = "Unknown"
if "last_greeted_user" not in st.session_state:
    st.session_state.last_greeted_user = ""
if "webcam_active" not in st.session_state:
    st.session_state.webcam_active = False

# Quick access
face_handler = st.session_state.face_handler
dialog_manager = st.session_state.dialog_manager
stt_handler = st.session_state.stt_handler
tts_handler = st.session_state.tts_handler

# -----------------------------------------------------------------------------
# Sidebar Configuration
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("🤖 EthioChatbot")
    st.subheader("Multilingual AI Assistant")
    st.write("An offline-capable dialog system featuring Face Recognition, Ignite Word switching, and Speech synthesis.")
    st.markdown("---")

    # Subsystems Status
    st.subheader("Subsystem Status")
    
    # Face Rec Status
    if FACE_REC_AVAILABLE:
        st.success("✅ Face Recognition: Loaded")
    else:
        st.error("❌ Face Recognition: Unimportable")
        st.info("💡 Run 'pip install face-recognition' to enable. Depends on CMake and dlib.")
        
    # Speech Recognition Status
    if STT_AVAILABLE:
        st.success("✅ Speech-to-Text: Active")
    else:
        st.error("❌ Speech-to-Text: Unimportable")
        st.info("💡 Run 'pip install SpeechRecognition' to enable.")

    # TTS Status
    if TTS_AVAILABLE:
        st.success("✅ Text-to-Speech: Active")
    else:
        st.error("❌ Text-to-Speech: Unimportable")
        st.info("💡 Run 'pip install pyttsx3' to enable.")

    st.markdown("---")

    # Language Control Panel
    st.subheader("Language Settings")
    
    # Display current active language
    curr_lang = dialog_manager.active_lang
    lang_info = config.LANGUAGES[curr_lang]
    st.metric(label="Active Language Mode", value=f"{lang_info['name']}")
    
    # Manual Override Selector
    lang_options = {info["name"]: code for code, info in config.LANGUAGES.items()}
    selected_lang_name = st.selectbox(
        "Manual Language Override",
        options=list(lang_options.keys()),
        index=list(lang_options.values()).index(curr_lang)
    )
    selected_lang_code = lang_options[selected_lang_name]
    if selected_lang_code != curr_lang:
        dialog_manager.active_lang = selected_lang_code
        st.rerun()

    st.markdown("---")

    # Face Registration Sub-Panel
    st.subheader("Face Registration")
    st.write("Register a new face embedding to recognize you.")
    
    new_face_name = st.text_input("Person Name", placeholder="e.g., Johannes")
    register_btn = st.button("Capture & Register Face")
    
    if register_btn:
        if not FACE_REC_AVAILABLE:
            st.error("Face recognition module is not installed.")
        elif not new_face_name or new_face_name.strip() == "":
            st.warning("Please enter a name first.")
        else:
            # Try capturing a frame from webcam
            temp_cap = cv2.VideoCapture(0)
            if not temp_cap.isOpened():
                st.error("Webcam not accessible to capture photo.")
            else:
                time.sleep(1.0) # Warm up camera
                ret, frame = temp_cap.read()
                temp_cap.release()
                
                if ret:
                    success = face_handler.add_known_face(new_face_name, frame)
                    if success:
                        st.success(f"Successfully registered face: {new_face_name}!")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("Failed to detect a face in the capture. Please face the camera and try again.")
                else:
                    st.error("Failed to read frame from webcam.")

# -----------------------------------------------------------------------------
# Main Application Layout
# -----------------------------------------------------------------------------
st.markdown("<div class='main-header'>EthioChatbot Dashboard</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Amharic, Oromifa, Arabic, and English Rule-Based Chatbot with Facial AI</div>", unsafe_allow_html=True)

# Layout: Column 1 (Camera & Info) | Column 2 (Dialogue System)
col1, col2 = st.columns([1.1, 1.0])

# -----------------------------------------------------------------------------
# Column 1: Webcam Feed & Local Processing
# -----------------------------------------------------------------------------
with col1:
    st.subheader("👁️ Facial Recognition Feed")
    
    # Checkbox to start/stop camera processing
    webcam_enabled = st.checkbox("Enable Real-time Webcam Feed", value=st.session_state.webcam_active)
    
    # Store camera checkbox state
    if webcam_enabled != st.session_state.webcam_active:
        st.session_state.webcam_active = webcam_enabled
        st.rerun()

    # Create a placeholder for the live video frame
    frame_placeholder = st.empty()
    
    if st.session_state.webcam_active:
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            st.error("Could not open webcam. Ensure it's connected and not in use by another app.")
            st.session_state.webcam_active = False
        else:
            logger.info("Started real-time webcam feed loop.")
            
            # Loop while the checkbox remains checked
            while st.session_state.webcam_active:
                ret, frame = cap.read()
                if not ret:
                    st.error("Failed to grab webcam frame.")
                    break
                
                # Detect and recognize faces in the frame
                # Limit frequency of heavy face recognition if needed, but standard loop works locally
                face_coords = face_handler.detect_faces(frame)
                recognition_results = face_handler.recognize_person(frame, face_coords)
                
                # Draw boxes and overlays
                annotated_frame = face_handler.draw_overlays(frame, recognition_results)
                
                # Identify the dominant recognized name in this frame
                frame_user = "Unknown"
                known_detections = [res["name"] for res in recognition_results if res["name"] != "Unknown"]
                if known_detections:
                    frame_user = known_detections[0] # Take first recognized face
                    
                # Update recognized user state
                if frame_user != st.session_state.recognized_user:
                    st.session_state.recognized_user = frame_user
                
                # Check for automatic greetings for newly recognized persons
                if frame_user != "Unknown" and frame_user != st.session_state.last_greeted_user:
                    # Greet user in active language
                    lang_code = dialog_manager.active_lang
                    
                    if lang_code == "en":
                        greet_text = f"Hello {frame_user}, how can I help you today?"
                    elif lang_code == "am":
                        greet_text = f"ሰላም {frame_user}፣ እንዴት ልረዳዎት እችላለሁ?"
                    elif lang_code == "om":
                        greet_text = f"Akkam {frame_user}, maal si gargaaruu danda'a?"
                    elif lang_code == "ar":
                        greet_text = f"مرحباً {frame_user}! كيف يمكنني مساعدتك اليوم؟"
                    else:
                        greet_text = f"Hello {frame_user}!"
                        
                    # Add to chat history
                    st.session_state.chat_history.append({"role": "bot", "text": greet_text})
                    st.session_state.last_greeted_user = frame_user
                    
                    # Synthesize voice output (non-blocking if possible, but standard playback)
                    # We run in a thread or direct local play
                    tts_handler.speak_output(greet_text, lang_code=lang_code, play_local=True)
                    st.rerun()

                # Convert OpenCV frame (BGR) to RGB for Streamlit rendering
                rgb_annotated = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                frame_placeholder.image(rgb_annotated, channels="RGB", use_container_width=True)
                
                # Short sleep to prevent CPU throttling (roughly 24 fps)
                time.sleep(0.04)
                
            cap.release()
            logger.info("Released webcam feed.")
            frame_placeholder.empty()
    else:
        # Show a placeholder image when camera is off
        placeholder_image = Image.new('RGB', (640, 480), color=(40, 44, 52))
        frame_placeholder.image(placeholder_image, caption="Webcam Feed Inactive", use_container_width=True)

    # Info Banner under Camera
    st.markdown("### 🏷️ Status Indicators")
    col_sub1, col_sub2 = st.columns(2)
    with col_sub1:
        st.metric(label="Identified Face", value=st.session_state.recognized_user)
    with col_sub2:
        lang_code = dialog_manager.active_lang
        st.metric(label="Language Mode", value=config.LANGUAGES[lang_code]["name"])

# -----------------------------------------------------------------------------
# Column 2: Dialogue System & Chat History
# -----------------------------------------------------------------------------
with col2:
    st.subheader("💬 Dialogue Interface")
    
    # Reset chat button
    if st.button("🗑️ Clear Conversation History", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.last_greeted_user = ""
        st.session_state.recognized_user = "Unknown"
        st.success("Conversation cleared!")
        time.sleep(1.0)
        st.rerun()

    # Conversation Display Box
    st.markdown("#### Chat History")
    
    # We display each message inside a Streamlit chat container
    chat_container = st.container()
    with chat_container:
        if not st.session_state.chat_history:
            st.info("No conversation history yet. Say 'Hello', 'ሰላም', 'Akkam', or 'مرحبا' to begin!")
        else:
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    with st.chat_message("user"):
                        st.write(msg["text"])
                else:
                    with st.chat_message("assistant"):
                        st.write(msg["text"])
                        # If there is a recorded audio path, provide a audio element
                        if "audio_path" in msg and msg["audio_path"] and os.path.exists(msg["audio_path"]):
                            with open(msg["audio_path"], 'rb') as f:
                                audio_bytes = f.read()
                            st.audio(audio_bytes, format="audio/mp3")

    st.markdown("---")
    
    # User Input Interface
    st.markdown("#### Enter Input")
    
    # Form layout for text input and speech
    user_text_input = st.text_input(
        "Type message & press Enter",
        key="user_raw_input",
        placeholder="Type here..."
    )
    
    col_input1, col_input2 = st.columns([1, 1])
    
    with col_input1:
        submit_btn = st.button("✉️ Send Text", use_container_width=True)
    with col_input2:
        voice_btn = st.button("🎙️ Voice Input (Listen)", use_container_width=True, disabled=not STT_AVAILABLE)

    # -------------------------------------------------------------------------
    # Dialogue Action Processing
    # -------------------------------------------------------------------------
    user_query = None
    
    # Handle Text submission
    if submit_btn and user_text_input.strip() != "":
        user_query = user_text_input
        
    # Handle Voice submission
    if voice_btn:
        st.warning("🎙️ System is listening... Speak now.")
        # Call Speech Recognition
        lang_code = dialog_manager.active_lang
        transcription = stt_handler.listen(lang_code=lang_code)
        
        if transcription:
            user_query = transcription
            st.success(f"Recognized Speech: '{transcription}'")
        else:
            st.error("Could not capture speech. Please ensure your mic is connected, or try typing.")

    # Process query if received
    if user_query:
        # 1. Add user query to chat history
        st.session_state.chat_history.append({"role": "user", "text": user_query})
        
        # 2. Get dialog manager response
        response_dict = dialog_manager.respond(user_query)
        bot_reply = response_dict["response"]
        lang_switched = response_dict["lang_switched"]
        new_lang = response_dict["active_lang"]
        
        # 3. Handle TTS voice synthesis (play_local=True for host, retrieve audio file path)
        audio_file_path = tts_handler.speak_output(bot_reply, lang_code=new_lang, play_local=True)
        
        # 4. Save response to chat history
        msg_entry = {"role": "bot", "text": bot_reply}
        if audio_file_path:
            msg_entry["audio_path"] = audio_file_path
            
        st.session_state.chat_history.append(msg_entry)
        
        # 5. Automatically rerun page to display updates
        st.rerun()