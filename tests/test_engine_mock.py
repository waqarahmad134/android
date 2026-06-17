"""End-to-end test of the generate() pipeline against the MockEngine.

Exercises parse -> validate -> voice mapping -> synthesize -> save_wav without
any model weights.
"""

import wave

from vibevoice_studio.config import SAMPLE_RATE, GenerationConfig
from vibevoice_studio.engine import MockEngine, make_engine
from vibevoice_studio.generate import generate, get_or_create_engine
from vibevoice_studio.voices import VoiceLibrary


def _write_silent_wav(path, seconds=0.2, sr=SAMPLE_RATE):
    n = int(seconds * sr)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"\x00\x00" * n)


def _library(tmp_path):
    voices = tmp_path / "voices"
    voices.mkdir()
    _write_silent_wav(voices / "en-Alice_woman.wav")
    _write_silent_wav(voices / "en-Carter_man.wav")
    lib = VoiceLibrary(voices, cache_dir=tmp_path / "cache")
    lib.discover()
    return lib


def test_make_engine_mock():
    assert isinstance(make_engine(GenerationConfig(), mock=True), MockEngine)


def test_generate_end_to_end_mock(tmp_path):
    lib = _library(tmp_path)
    out = tmp_path / "out.wav"
    cfg = GenerationConfig()
    engine = get_or_create_engine(cfg, mock=True)

    result = generate(
        script_text="Speaker 1: Hello there.\nSpeaker 2: General Kenobi.",
        voice_assignment={1: "Alice", 2: "Carter"},
        library=lib,
        cfg=cfg,
        engine=engine,
        out_path=out,
    )

    assert result.num_speakers == 2
    assert result.sample_rate == SAMPLE_RATE
    assert result.duration_seconds > 0
    assert out.is_file()
    # Confirm a readable WAV was written.
    with wave.open(str(out), "rb") as w:
        assert w.getframerate() == SAMPLE_RATE
        assert w.getnframes() > 0


def test_generate_invalid_script_raises(tmp_path):
    lib = _library(tmp_path)
    cfg = GenerationConfig()
    engine = get_or_create_engine(cfg, mock=True)
    import pytest

    from vibevoice_studio.generate import GenerationError

    with pytest.raises(GenerationError):
        generate(
            script_text="   ",
            voice_assignment={},
            library=lib,
            cfg=cfg,
            engine=engine,
        )
