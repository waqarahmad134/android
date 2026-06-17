import wave

import pytest

from vibevoice_studio.script_parser import parse_script
from vibevoice_studio.voices import VoiceLibrary, build_speaker_voice_paths


def _write_silent_wav(path, seconds=0.2, sr=24000):
    n = int(seconds * sr)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"\x00\x00" * n)


def test_discover_and_name_convention(tmp_path):
    voices = tmp_path / "voices"
    voices.mkdir()
    _write_silent_wav(voices / "en-Alice_woman.wav")
    _write_silent_wav(voices / "en-Carter_man.wav")

    lib = VoiceLibrary(voices, cache_dir=tmp_path / "cache")
    found = lib.discover()
    assert {v.name for v in found} == {"Alice", "Carter"}

    alice = lib.get("Alice")
    assert alice.language == "en"
    assert alice.gender == "woman"
    assert lib.names() == ["Alice", "Carter"]


def test_register_cloned_adds_voice(tmp_path):
    voices = tmp_path / "voices"
    voices.mkdir()
    sample = tmp_path / "sample.wav"
    _write_silent_wav(sample)

    lib = VoiceLibrary(voices, cache_dir=tmp_path / "cache")
    lib.discover()
    voice = lib.register_cloned(sample, label="MyVoice")
    assert voice.is_cloned
    assert "MyVoice" in lib.names()
    assert lib.get("MyVoice").is_cloned


def test_build_speaker_voice_paths_order(tmp_path):
    voices = tmp_path / "voices"
    voices.mkdir()
    _write_silent_wav(voices / "en-Alice_woman.wav")
    _write_silent_wav(voices / "en-Carter_man.wav")

    lib = VoiceLibrary(voices, cache_dir=tmp_path / "cache")
    lib.discover()

    parsed = parse_script("Speaker 1: hi\nSpeaker 2: yo")
    paths = build_speaker_voice_paths(parsed, {1: "Alice", 2: "Carter"}, lib)
    assert [p.name for p in paths] == ["en-Alice_woman.wav", "en-Carter_man.wav"]


def test_build_speaker_voice_paths_missing_assignment(tmp_path):
    voices = tmp_path / "voices"
    voices.mkdir()
    _write_silent_wav(voices / "en-Alice_woman.wav")
    lib = VoiceLibrary(voices, cache_dir=tmp_path / "cache")
    lib.discover()
    parsed = parse_script("Speaker 1: hi\nSpeaker 2: yo")
    with pytest.raises(ValueError):
        build_speaker_voice_paths(parsed, {1: "Alice"}, lib)
