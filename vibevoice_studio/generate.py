"""The single high-level generation entrypoint shared by the UI and CLI.

Both ``app.py`` and ``cli.py`` assemble their arguments and call
:func:`generate` — there is no model or audio logic anywhere else in the
front-ends.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import GenerationConfig
from .engine import GenerationEngine, make_engine
from .script_parser import parse_script, validate_script
from .utils import audio_duration_seconds, save_wav, setup_logging
from .voices import Voice, VoiceLibrary, build_speaker_voice_paths

logger = setup_logging()

# Process-level engine cache so the model loads only once per configuration.
_ENGINE_CACHE: dict[tuple, GenerationEngine] = {}


class GenerationError(ValueError):
    """Raised when a script or voice assignment is invalid."""


@dataclass
class GenerateResult:
    audio: object  # 1-D numpy float array
    sample_rate: int
    out_path: Path | None
    num_speakers: int
    duration_seconds: float
    warnings: list[str] = field(default_factory=list)


def _cache_key(cfg: GenerationConfig, mock: bool) -> tuple:
    return (cfg.model_id, cfg.device, cfg.dtype, cfg.attn_implementation, mock)


def get_or_create_engine(cfg: GenerationConfig, mock: bool = False) -> GenerationEngine:
    """Return a cached engine for ``cfg`` (so weights load once), creating if needed."""
    key = _cache_key(cfg, mock)
    engine = _ENGINE_CACHE.get(key)
    if engine is None:
        engine = make_engine(cfg, mock=mock)
        _ENGINE_CACHE[key] = engine
    return engine


def generate(
    script_text: str,
    voice_assignment: dict[int, str],
    library: VoiceLibrary,
    cfg: GenerationConfig,
    engine: GenerationEngine,
    cloned_voices: dict[str, Voice] | None = None,
    out_path: str | Path | None = None,
) -> GenerateResult:
    """Turn a multi-speaker script into audio.

    Pipeline: parse -> validate -> resolve voices -> (lazy-load engine) ->
    synthesize -> optionally save a WAV.
    """
    parsed = parse_script(script_text)
    errors = validate_script(parsed)
    if errors:
        raise GenerationError("; ".join(errors))

    sample_paths = build_speaker_voice_paths(
        parsed, voice_assignment, library, cloned_voices
    )

    if not engine.is_loaded:
        engine.load()

    audio, sample_rate = engine.synthesize(parsed.to_engine_text(), sample_paths, cfg)

    saved: Path | None = None
    if out_path is not None:
        saved = save_wav(out_path, audio, sample_rate)
        logger.info("Wrote %s", saved)

    return GenerateResult(
        audio=audio,
        sample_rate=sample_rate,
        out_path=saved,
        num_speakers=parsed.num_speakers(),
        duration_seconds=audio_duration_seconds(audio, sample_rate),
        warnings=[],
    )
