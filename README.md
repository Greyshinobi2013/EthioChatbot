# EthioChatbot MVP

Offline, rule-based voice assistant for GPU Desktop and Raspberry Pi 4.

## Quick Start (Local Venv)

1. **Install Dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Download Models:**
   - **Face Model:** Automatically downloaded by `face_recognition` (dlib) on first run.
   - **VOSK ASR Model:** 
     - English: [vosk-model-small-en-us-0.15](https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip)
     - Amharic: [vosk-model-am-0.22](https://alphacephei.com/vosk/models/vosk-model-am-0.22.zip) (if available) or generic multi-lang.
     - Place in `models/` folder.

3. **Run Backend:**
   ```bash
   python backend.py
   ```

4. **Run Frontend:**
   ```bash
   streamlit run app.py
   ```

## Architecture

```text
+----------------+      +-------------------+      +-----------------+
|  Streamlit UI  | <--> |  FastAPI Backend  | <--> |  Rule Engine    |
+----------------+      +---------+---------+      +-----------------+
                                  |
                +-----------------+-----------------+
                |                 |                 |
        +-------v-------+  +------v-------+  +------v-------+
        | Face Service  |  | Audio Service|  | Greeting Q   |
        | (Embeddings)  |  | (VOSK ASR)   |  | (Staggered)  |
        +---------------+  +--------------+  +--------------+
```

## Pi Deployment Notes
- **Face:** Use `TFLite` or `ONNX` version of MobileFaceNet for faster inference.
- **ASR:** Use `vosk-model-small` variants.
- **Quantization:** Apply int8 quantization to models.
- **Audio:** Use pre-synthesized WAVs to save CPU cycles.

## Privacy Statement
Only facial embeddings (vector representation) are stored in `data/embeddings/users.pkl`. No raw images are retained after enrollment. Data is local and never leaves the device.
