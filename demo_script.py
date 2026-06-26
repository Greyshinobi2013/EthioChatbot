import cv2
import numpy as np
import requests
import os

# Simulated enrollment and recognition script
def demo():
    print("--- Starting EthioChatbot Demo ---")
    
    # 1. Create fake enrollment images (blue squares for demo)
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(img, "User Face", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
    
    enroll_path = "data/enrollment/demo_user"
    os.makedirs(enroll_path, exist_ok=True)
    for i in range(5):
        cv2.imwrite(f"{enroll_path}/face_{i}.jpg", img)
    
    print("Step 1: Enrollment Data Prepared.")
    
    # 2. Trigger Recognition (Simulated)
    # Note: In a real demo, we'd send these to the endpoints
    print("Step 2: Backend/Frontend ready for manual testing via Streamlit.")
    print("Checklist:")
    print("- [ ] App starts on http://localhost:8501")
    print("- [ ] Backend starts on http://localhost:8000")
    print("- [ ] Enrollment captures 5 frames")
    print("- [ ] Recognition triggers 'Greeting Queue' in logs")

if __name__ == "__main__":
    demo()
