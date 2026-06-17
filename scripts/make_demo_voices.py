#!/usr/bin/env python3
"""Generate placeholder preset voices so the app is runnable immediately.

These are short synthetic tones — they exist only so the voice menus are
populated and you can try the workflow (especially mock mode) right away.

**Replace them with real 10–30s speech samples** before doing real generation,
otherwise the model has nothing meaningful to clone. See assets/voices/README.md.
"""

from __future__ import annotations

import math
import wave
from pathlib import Path

VOICES_DIR = Path(__file__).resolve().parent.parent / "assets" / "voices"
SAMPLE_RATE = 24000

# name -> (language, gender, base frequency Hz)
DEMO_VOICES = {
    "Alice": ("en", "woman", 220.0),
    "Carter": ("en", "man", 130.0),
    "Mia": ("en", "woman", 260.0),
    "Theo": ("en", "man", 110.0),
}


def _write_tone(path: Path, freq: float, seconds: float = 3.0) -> None:
    n = int(seconds * SAMPLE_RATE)
    frames = bytearray()
    for i in range(n):
        # Gentle amplitude envelope so it sounds less harsh.
        env = 0.3 * math.sin(math.pi * i / n)
        sample = int(env * 32767 * math.sin(2.0 * math.pi * freq * i / SAMPLE_RATE))
        frames += int(sample).to_bytes(2, "little", signed=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(bytes(frames))


def main() -> None:
    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    for name, (lang, gender, freq) in DEMO_VOICES.items():
        path = VOICES_DIR / f"{lang}-{name}_{gender}.wav"
        _write_tone(path, freq)
        print(f"wrote {path}")
    print("\nPlaceholder voices created. Replace them with real speech samples for real output.")


if __name__ == "__main__":
    main()
