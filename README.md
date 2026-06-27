# Offline Multimodal Chatbot

A fully offline, rule-based chatbot that combines **face recognition**,
**offline speech recognition**, and **pre-recorded multilingual audio**
to deliver scripted dialog scenarios — with real-time interruption
handling so the bot pauses politely if you start talking while it's
mid-sentence.

Everything runs on your own machine. No part of the pipeline (face
matching, wake-word detection, transcription, or playback) calls out
to the internet.

---

## 1. What it does

1. **Watches the webcam.** When a known, enrolled face is detected for
   a few consecutive frames, the bot greets that person with a
   pre-recorded audio clip.
2. **Listens for a wake word** ("Hello", "ሰላም", etc.) to decide which
   language to run the conversation in.
3. **Plays a scripted dialog scenario** in that language — a sequence
   of pre-recorded audio clips defined in a JSON file, not a
   generative model.
4. **Listens while it talks.** A lightweight voice-activity detector
   (VAD) runs continuously in the background. If you start speaking
   while a clip is playing, the bot pauses, says "please wait," and
   resumes (or restarts) the clip a couple of seconds after you stop.
5. Everything is controllable from a **Streamlit dashboard**: enroll
   faces, watch the live recognition feed, trigger scenarios manually,
   and tune recognition/VAD sensitivity.

---

## 2. Project layout

```
offline_chatbot/
├── app/
│   ├── streamlit_app.py        # Dashboard entrypoint (run this with `streamlit run`)
│   ├── core/
│   │   ├── config.py           # Paths, logging, tunable Settings dataclass
│   │   ├── face_engine.py      # dlib/OpenCV: enrollment + recognition
│   │   ├── speech_engine.py    # Whisper transcription, wake-word match, VAD
│   │   ├── audio_player.py     # pygame.mixer playback, pause/resume/restart
│   │   ├── dialog_manager.py   # Pure state machine: user+lang+scenario -> audio path
│   │   ├── orchestrator.py     # Wires the above into one session state machine
│   │   └── bootstrap.py        # Constructs all of the above, degrading gracefully
│   ├── data/
│   │   └── dialog_config.json  # All languages, wake words, scenarios, audio mappings
│   ├── assets/audio/{en,am}/   # The actual .wav response clips
│   ├── enrolled_faces/         # face_db.pkl (embeddings) lives here at runtime
│   └── models/                 # dlib's pretrained .dat model files go here (you download these)
├── scripts/
│   └── generate_placeholder_audio.py  # Makes stand-in tone clips so the app runs before real recordings exist
└── requirements.txt
```

**Design principle:** `core/dialog_manager.py` and `core/orchestrator.py`
contain zero Streamlit-specific code. They're plain Python classes you
could drive from a CLI, a test suite, or a different UI entirely. The
Streamlit file only reads status and calls public methods.

---

## 3. Setup

### 3.1 Python environment

```bash
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

`dlib` and `torch` (a Whisper dependency) both compile/download large
binaries — expect this step to take a few minutes, and make sure you
have a C++ build toolchain installed for `dlib` if a pre-built wheel
isn't available for your platform.

### 3.2 Download the dlib face models

These two pretrained model files are not bundled with the repo (they're
tens of MB each) — download them into `app/models/`:

- `shape_predictor_5_face_landmarks.dat`
- `dlib_face_recognition_resnet_model_v1.dat`

Both are published on dlib's official model page
(`dlib.net/files/`, distributed `.bz2`-compressed — decompress before
placing them in `app/models/`). If these files are missing, the
dashboard will still launch but face recognition will be disabled with
a clear on-screen message — the rest of the app remains usable.

### 3.3 Whisper model

`openai-whisper` downloads its model weights to a local cache
(`~/.cache/whisper`) the first time you run with a given model size —
this is a one-time, one-machine download, not a live API call; once
cached, transcription runs fully offline. Pick the size in **Settings**
in the dashboard. `base` is a reasonable default (fast, decent
accuracy); use `small` or `medium` if you have CPU/GPU headroom and
want better accuracy, especially for Amharic.

### 3.4 Audio device check (for interruption detection)

`sounddevice` binds to the system's PortAudio library, and
`webrtcvad` is used for fast voice-activity detection. If either is
missing, the affected feature degrades gracefully:

- No `sounddevice`/PortAudio → wake-word listening and interruption
  detection are disabled; manual scenario buttons in the dashboard
  still work.
- No `webrtcvad` → interruption detection automatically falls back to
  a simpler energy-threshold (RMS) check. Less robust in noisy rooms,
  but still functional.

### 3.5 Generate placeholder audio (optional, for a quick first run)

Real recordings aren't included in the repo. To try the whole pipeline
immediately, generate stand-in tone clips for every audio path
referenced in `dialog_config.json`:

```bash
python scripts/generate_placeholder_audio.py
```

This creates short audible tones (different pitch per language) at
every path the JSON expects, so nothing 404s during a demo. Re-run
with `--force` to regenerate; it never overwrites real recordings you've
already added unless you pass that flag.

---

## 4. Running the app

```bash
streamlit run app/streamlit_app.py
```

This opens the dashboard in your browser (locally — no data leaves
your machine). The sidebar has four pages:

- **Dashboard** — webcam feed with recognition overlay, live session
  state, wake-word test button, manual scenario triggers.
- **Enroll Face** — register a new user via webcam snapshots or a
  photo upload.
- **Manage Scenarios** — view the current languages/scenarios, and
  edit `dialog_config.json` directly from a text box.
- **Settings** — tune face-match tolerance, Whisper model size, VAD
  aggressiveness, and how the bot resumes after an interruption
  (restart the clip vs. continue from where it paused).

### Typical first run

1. Go to **Enroll Face**, type a name, take 3–5 webcam snapshots.
2. Go to **Dashboard**, toggle the camera on. After a few consistent
   frames recognizing your face, the state changes to "Listening for
   wake word."
3. Click **🎤 Listen for wake word** and say "Hello" (or "ሰላም" for
   Amharic) within the recording window.
4. The bot plays its greeting, then starts the default `welcome`
   scenario. Try talking while a clip plays — the dashboard's status
   panel will show "Paused — please wait," and it resumes a couple of
   seconds after you stop.

---

## 5. How the dialog configuration works

`app/data/dialog_config.json` is the single source of truth for
languages, wake words, and scenario scripts. A content author can add
a new language or scenario without touching any Python code.

```jsonc
{
  "languages": {
    "en": { "name": "English", "wake_words": ["hello", "hi"], "default_greeting": "audio/en/greeting_default.wav" },
    "am": { "name": "Amharic", "wake_words": ["selam"], "wake_words_native": ["ሰላም"], "default_greeting": "audio/am/greeting_default.wav" }
  },
  "scenarios": {
    "welcome": {
      "entry_step": "start",
      "steps": {
        "start": { "en": "audio/en/welcome_start.wav", "am": "audio/am/welcome_start.wav", "interruptible": true, "next": "menu" },
        "menu":  { "en": "audio/en/welcome_menu.wav",  "am": "audio/am/welcome_menu.wav",  "interruptible": true, "next": null }
      }
    }
  },
  "default_scenario": "welcome"
}
```

- **`languages`** — each entry defines display name, the wake word(s)
  that activate it (Whisper transcribes whatever language was spoken;
  matching is a case-insensitive substring check against this list,
  which is what lets one listener cover multiple scripts/languages
  without a dedicated model per wake word), and a fallback greeting.
- **`scenarios.<id>.steps.<id>`** — one dialog "turn." `next` points to
  the following step id, or `null` to end the scenario.
  `interruptible: false` is for short safety-critical lines you don't
  want barge-in to skip (e.g. you might mark the closing "goodbye" line
  as non-interruptible).
- **`user_greetings`** — optional per-user, per-language greeting
  overrides (e.g. a personalized welcome for a specific enrolled
  name), falling back to `user_greetings.default`, and finally to the
  language's own `default_greeting` if nothing else matches.

### Adding a new language

1. Add an entry under `languages` with its wake words and a default
   greeting path.
2. Add that language's key (e.g. `"fr"`) to every scenario step you
   want available in that language.
3. Drop the corresponding `.wav` files under `app/assets/audio/<code>/`.

### Adding a new scenario

1. Add a new key under `scenarios` with an `entry_step` and a `steps`
   map, following the same shape as `welcome`.
2. Reference it from the dashboard's **Scenario** dropdown (it's
   populated automatically from the JSON — no code change needed), or
   wire a wake-word/intent to it in `orchestrator.py` if you want it
   reachable some other way than the manual dropdown.

### Audio format

Any format `pygame.mixer.music` supports works (`.wav`, `.ogg`, `.mp3`
on most platforms), but mono 16-bit PCM `.wav` at 16 kHz is the safest
cross-platform choice and what the placeholder generator produces.

---

## 6. Architecture notes

### 6.1 Why face confirmation requires several consecutive frames

A single frame's recognition result is treated only as a *candidate*.
`ChatbotOrchestrator.process_frame()` requires the same `user_id` to
match across `Settings.face_min_detections_to_confirm` consecutive
frames before firing the greeting — this avoids a flickering
misdetection (bad lighting, a partial profile view) from triggering a
greeting for the wrong person, or repeatedly re-triggering as someone
moves in and out of frame.

### 6.2 Why interruption detection doesn't use Whisper

Wake-word detection can afford a multi-second round trip through
Whisper because it only runs once, on demand. Interruption detection
needs to react in a fraction of a second the moment someone starts
talking — running a full transcription model in that loop would be far
too slow. Instead, `VoiceActivityMonitor` uses `webrtcvad`'s
frame-level voiced/unvoiced classifier (falling back to a simple
RMS-energy gate if that's not installed) on a dedicated background
thread, polling small ~30ms audio frames and requiring a handful of
consecutive voiced frames before calling back into the orchestrator.
This is also why VAD and audio playback are genuinely concurrent
rather than simulated: `AudioPlayer.play()` hands playback off to
pygame's own mixer thread and returns immediately, while
`VoiceActivityMonitor` runs its own polling loop on a second thread —
neither blocks the other.

### 6.3 Resume vs. restart after an interruption

Configurable in **Settings → "After an interruption, the chatbot
should..."**:

- **Restart** (default): replays the current clip from the beginning.
  Generally clearer for short dialog lines, since the user likely
  missed the very start of the clip anyway.
- **Resume**: continues from the exact position where playback was
  paused.

### 6.4 Graceful degradation

`core/bootstrap.py` treats face recognition and speech recognition as
*optional* — if `dlib`'s model files or Whisper aren't available, the
corresponding engine is simply `None` and the dashboard shows a clear
banner, while everything else (manual scenario playback, the JSON
editor, settings) keeps working. **Audio playback is the one hard
requirement** (a chatbot that can't play its pre-recorded responses
has no way to do anything), so a missing `pygame` install raises a
specific, actionable error at startup instead of failing confusingly
mid-conversation.

---

## 7. Extending the system

| Want to... | Where to look |
|---|---|
| Add a new language | `dialog_config.json` only — see §5 |
| Add a new scenario / branch the conversation on a keyword | `dialog_config.json` for the script; `orchestrator.trigger_scenario()` or `listen_for_wake_word()` if you want it reachable by voice |
| Change how strict face matching is | Settings page, or `Settings.face_match_tolerance` in `core/config.py` |
| Swap in a stronger Whisper model | Settings page (`base` → `small`/`medium`); restart the app to reload |
| Replace pygame with another audio backend | Only `core/audio_player.py` needs to change — its public interface (`play`, `pause_for_interruption`, `resume_or_restart`, `stop`, `is_busy`, `status`) is what the orchestrator depends on |
| Use a different face recognition backend (e.g. a different embedding model) | Only `core/face_engine.py` needs to change — keep `enroll`, `identify`, `list_users` with the same signatures |
| Drive the chatbot from something other than Streamlit | Import `core/bootstrap.build_orchestrator()` directly; the orchestrator has no UI framework dependency |

---

## 8. Known limitations

- Wake-word and scenario-trigger matching is keyword/substring based,
  not full natural-language understanding — by design, since this is
  a rule-based system, not a generative one.
- The Streamlit webcam loop captures a bounded burst of frames per
  script rerun (a consequence of Streamlit's execution model, which
  reruns top-to-bottom on each interaction) rather than a true
  infinite live loop; toggling the camera off and back on resets it.
- `_best_match` in `face_engine.py` does a linear scan over all
  enrolled embeddings per frame; fine for the tens-of-users scale this
  is built for, but would want a proper nearest-neighbor index (e.g.
  a KD-tree) for a large enrollment base.
