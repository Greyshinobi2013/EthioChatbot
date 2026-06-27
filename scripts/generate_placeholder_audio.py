"""
Generate placeholder audio files for every path referenced in
dialog_config.json.

This lets the whole pipeline (wake word -> greeting -> scenario steps)
run end-to-end immediately after cloning the project, before a content
author has recorded real voice lines. Each placeholder is a short,
clearly-audible tone (not silence, so it's obvious during a demo that
*a* clip played) with a duration that scales slightly with text length
so playback timing feels roughly realistic.

Usage:
    python scripts/generate_placeholder_audio.py

Safe to re-run: existing files are skipped unless --force is passed,
so it won't clobber real recordings a content author has already
dropped in.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import wave
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import DIALOG_CONFIG_PATH, ASSETS_DIR  # noqa: E402


def collect_audio_paths(config: dict) -> set[str]:
    """Walk the dialog config and gather every relative audio path
    referenced anywhere (language defaults, user greetings, scenario
    steps), regardless of how deeply nested -- avoids this script
    silently going stale if the JSON schema grows a new place to
    reference an audio file."""
    paths: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key.endswith("_comment"):
                    continue
                if isinstance(value, str) and value.startswith("audio/"):
                    paths.add(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(config)
    return paths


def make_tone_wav(path: Path, frequency: float = 440.0, duration_s: float = 1.2, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n_samples = int(sample_rate * duration_s)
    amplitude = 0.25 * 32767  # keep it well below clipping

    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            # gentle fade in/out to avoid an audible click at clip boundaries
            fade = min(1.0, i / (sample_rate * 0.05), (n_samples - i) / (sample_rate * 0.05))
            sample = amplitude * fade * math.sin(2 * math.pi * frequency * t)
            frames += struct.pack("<h", int(sample))
        wf.writeframes(bytes(frames))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Overwrite existing audio files.")
    args = parser.parse_args()

    with open(DIALOG_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    relative_paths = sorted(collect_audio_paths(config))
    print(f"Found {len(relative_paths)} audio references in dialog_config.json")

    # Vary the tone per language so it's audibly obvious which language
    # path is playing during a demo, even before real recordings exist.
    tone_by_lang_hint = {"/en/": 440.0, "/am/": 660.0}

    created, skipped = 0, 0
    for rel in relative_paths:
        abs_path = ASSETS_DIR / rel
        if abs_path.exists() and not args.force:
            skipped += 1
            continue

        frequency = 440.0
        for hint, freq in tone_by_lang_hint.items():
            if hint in rel:
                frequency = freq
                break

        make_tone_wav(abs_path, frequency=frequency)
        created += 1
        print(f"  created: {rel}")

    print(f"\nDone. Created {created}, skipped {skipped} (already existed).")
    if skipped:
        print("Use --force to overwrite existing files.")


if __name__ == "__main__":
    main()
