import streamlit as st
import json

PATH = "config/dialog_config.json"

with open(PATH) as f:
    data = json.load(f)

st.title("🧩 Scenarios")

text = st.text_area("Edit JSON", json.dumps(data, indent=2), height=400)

if st.button("Save"):
    try:
        parsed = json.loads(text)
        with open(PATH, "w") as f:
            json.dump(parsed, f, indent=2)
        st.success("Saved ✅")
    except:
        st.error("Invalid JSON")

if st.button("Reload"):
    st.rerun()