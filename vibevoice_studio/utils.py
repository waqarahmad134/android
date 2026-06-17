"""Small audio and filesystem helpers.

Audio libraries (``soundfile``, ``numpy``, ``librosa``) are imported lazily so
this module stays importable in minimal environments. Functions that genuinely
need them raise a clear error if they are missing.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from .config import SAMPLE_RATE

_LOGGER_NAME = "vibevoice_studio"


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure and return the package logger."""
    logger = logging.getLogger(_LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(level.upper())
    return logger


def slugify(text: str, max_length: int = 48) -> str:
    """Turn arbitrary text into a safe filename fragment."""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return (text[:max_length].rstrip("-")) or "audio"


def timestamped_name(prefix: str = "podcast", ext: str = "wav") -> str:
    """Return a unique, sortable filename like ``podcast-20260617-120000.wav``."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{slugify(prefix)}-{stamp}.{ext}"


def _require(module_name: str):
    try:
        return __import__(module_name)
    except Exception as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            f"'{module_name}' is required for this operation. Install the project "
            "requirements with: pip install -r requirements.txt"
        ) from exc


def save_wav(path: str | Path, audio, sample_rate: int = SAMPLE_RATE) -> Path:
    """Write a mono float waveform to ``path`` as a WAV file."""
    sf = _require("soundfile")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, sample_rate)
    return path


def load_and_normalize_audio(path: str | Path, target_sr: int = SAMPLE_RATE):
    """Load an audio file as mono float32 resampled to ``target_sr``.

    Returns a 1-D numpy array. Used to normalise uploaded voice-cloning samples.
    """
    sf = _require("soundfile")
    np = _require("numpy")

    audio, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if getattr(audio, "ndim", 1) > 1:
        audio = audio.mean(axis=1)  # downmix to mono

    if sr != target_sr:
        try:
            import librosa  # noqa: PLC0415

            audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
        except Exception:
            # Fallback: simple linear resample so we never hard-fail on a sample.
            duration = audio.shape[0] / float(sr)
            new_len = max(1, int(round(duration * target_sr)))
            x_old = np.linspace(0.0, 1.0, num=audio.shape[0], endpoint=False)
            x_new = np.linspace(0.0, 1.0, num=new_len, endpoint=False)
            audio = np.interp(x_new, x_old, audio).astype("float32")

    return audio


def audio_duration_seconds(audio, sample_rate: int = SAMPLE_RATE) -> float:
    """Return the duration of a waveform in seconds."""
    n = int(getattr(audio, "shape", [len(audio)])[0])
    return n / float(sample_rate)
