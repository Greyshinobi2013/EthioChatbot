from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from services.face_service import FaceService
from services.audio_service import AudioService
from services.rules import RuleEngine
import cv2
import numpy as np
import threading
import time

app = FastAPI()
face_svc = FaceService()
# Note: Models need to be downloaded first
# audio_svc = AudioService() 
rule_engine = RuleEngine()

greeting_queue = []
queue_lock = threading.Lock()

def process_greeting_queue():
    while True:
        if greeting_queue:
            with queue_lock:
                task = greeting_queue.pop(0)
            # Execute greeting with stagger delay
            print(f"Processing greeting for {task['name']}")
            time.sleep(8) # Stagger delay
        time.sleep(1)

threading.Thread(target=process_greeting_queue, daemon=True).start()

@app.post("/enroll")
async def enroll(name: str = Form(...), files: list[UploadFile] = File(...)):
    images = []
    for file in files:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        images.append(img)
    
    success = face_svc.enroll(name, images)
    return {"status": "success" if success else "failed"}

@app.post("/recognize")
async def recognize(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    names = face_svc.recognize(img)
    for name in names:
        if name != "Unknown" and face_svc.check_cooldown(name):
            with queue_lock:
                greeting_queue.append({"name": name, "timestamp": time.time()})
    
    return {"recognized": names}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
