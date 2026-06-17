"""Voice library: preset voices on disk plus session-cloned voices.

Preset voice samples live in ``assets/voices/`` as WAV files. A loose naming
convention of ``<lang>-<Name>_<gender>.wav`` (e.g. ``en-Alice_woman.wav``) is
parsed for nicer display, but any ``*.wav`` file is usable.

Voice cloning is just "use this audio sample as the reference for a speaker":
an uploaded sample is normalised, cached to disk, and registered as a
:class:`Voice` that can be assigned to any speaker exactly like a preset.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import MAX_SPEAKERS
from .script_parser import ParsedScript
from .utils import load_and_normalize_audio, save_wav, slugify


@dataclass
class Voice:
    """A reference voice sample, either a bundled preset or a cloned upload."""

    name: str
    path: Path
    gender: str | None = None
    language: str | None = None
    is_cloned: bool = False


def _parse_voice_filename(path: Path) -> Voice:
    """Best-effort parse of the ``<lang>-<Name>_<gender>.wav`` convention."""
    stem = path.stem
    language: str | None = None
    gender: str | None = None
    name = stem

    if "-" in stem:
        language, _, name = stem.partition("-")
    if "_" in name:
        name, _, gender = name.rpartition("_")

    return Voice(
        name=name or stem,
        path=path,
        gender=gender or None,
        language=language or None,
        is_cloned=False,
    )


class VoiceLibrary:
    """Discover preset voices and track session-cloned voices."""

    def __init__(self, voices_dir: Path, cache_dir: Path | None = None):
        self.voices_dir = Path(voices_dir)
        self.cache_dir = Path(cache_dir) if cache_dir else self.voices_dir.parent.parent / "outputs" / ".cache"
        self._presets: dict[str, Voice] = {}
        self._cloned: dict[str, Voice] = {}

    # -- discovery -----------------------------------------------------------

    def discover(self) -> list[Voice]:
        """(Re)scan the voices directory for preset ``*.wav`` files."""
        self._presets = {}
        if self.voices_dir.is_dir():
            for wav in sorted(self.voices_dir.glob("*.wav")):
                voice = _parse_voice_filename(wav)
                self._presets[voice.name] = voice
        return list(self._presets.values())

    def names(self) -> list[str]:
        """All selectable voice names (presets first, then cloned)."""
        if not self._presets:
            self.discover()
        return list(self._presets.keys()) + list(self._cloned.keys())

    def get(self, name: str) -> Voice:
        if not self._presets:
            self.discover()
        if name in self._cloned:
            return self._cloned[name]
        if name in self._presets:
            return self._presets[name]
        raise KeyError(f"Unknown voice: {name!r}. Available: {self.names()}")

    # -- cloning -------------------------------------------------------------

    def register_cloned(self, audio_path: str | Path, label: str = "My Voice") -> Voice:
        """Normalise an uploaded sample and register it as a cloned voice."""
        audio = load_and_normalize_audio(audio_path)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        dest = self.cache_dir / f"clone-{slugify(label)}.wav"
        save_wav(dest, audio)
        voice = Voice(name=label, path=dest, is_cloned=True)
        self._cloned[label] = voice
        return voice

    @property
    def cloned(self) -> dict[str, Voice]:
        return dict(self._cloned)


def build_speaker_voice_paths(
    parsed: ParsedScript,
    assignment: dict[int, str],
    library: VoiceLibrary,
    cloned: dict[str, Voice] | None = None,
) -> list[Path]:
    """Resolve each speaker to a reference sample path, in speaker order.

    ``assignment`` maps a 1-based speaker index to a voice name. The returned
    list is aligned to ``parsed.speaker_indices`` — one sample per distinct
    speaker — which is the order the VibeVoice processor expects.
    """
    cloned = cloned or {}
    paths: list[Path] = []
    available_names = set(library.names()) | set(cloned.keys())

    for index in parsed.speaker_indices:
        if index not in assignment or not assignment[index]:
            raise ValueError(f"No voice assigned to Speaker {index}.")
        name = assignment[index]
        if name not in available_names:
            raise ValueError(f"Speaker {index} assigned unknown voice {name!r}.")
        voice = cloned[name] if name in cloned else library.get(name)
        paths.append(Path(voice.path))

    if len(paths) > MAX_SPEAKERS:
        raise ValueError(f"Too many speakers ({len(paths)} > {MAX_SPEAKERS}).")
    return paths
