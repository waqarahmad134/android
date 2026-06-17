#!/usr/bin/env python3
"""Command-line interface for VibeVoice Studio.

Generate audio from a multi-speaker script file without launching the web UI.

Example::

    python cli.py --script assets/text_examples/1_podcast_2p.txt \\
        --voice "Speaker 1=Alice" --voice "Speaker 2=Carter" \\
        --out outputs/episode1.wav

Voice cloning::

    python cli.py --script story.txt \\
        --clone "MyVoice=/path/to/sample.wav" \\
        --voice "Speaker 1=MyVoice" --out outputs/story.wav
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from vibevoice_studio.config import AppPaths, GenerationConfig
from vibevoice_studio.device import describe_runtime
from vibevoice_studio.engine import force_mock_env
from vibevoice_studio.generate import (
    GenerationError,
    generate,
    get_or_create_engine,
)
from vibevoice_studio.utils import setup_logging, timestamped_name
from vibevoice_studio.voices import VoiceLibrary

logger = setup_logging()


def _speaker_index(label: str) -> int:
    """Parse 'Speaker 2' or '2' into the integer 2."""
    token = label.strip().lower().replace("speaker", "").strip()
    if not token.isdigit():
        raise argparse.ArgumentTypeError(f"Invalid speaker label: {label!r}")
    return int(token)


def _parse_kv(items: list[str], what: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit(f"--{what} expects KEY=VALUE, got: {item!r}")
        key, _, value = item.partition("=")
        out[key.strip()] = value.strip()
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="VibeVoice Studio — local audio generator (CLI)")
    p.add_argument("--script", required=True, help="Path to a multi-speaker script .txt file")
    p.add_argument(
        "--voice",
        action="append",
        default=[],
        metavar="SPEAKER=VOICE",
        help='Assign a voice to a speaker, e.g. --voice "Speaker 1=Alice" (repeatable)',
    )
    p.add_argument(
        "--clone",
        action="append",
        default=[],
        metavar="LABEL=PATH",
        help='Register a cloned voice from an audio sample, e.g. --clone "MyVoice=sample.wav"',
    )
    p.add_argument("--out", help="Output WAV path (default: outputs/<timestamp>.wav)")
    p.add_argument("--model-id", default=None, help="Override the HuggingFace model id")
    p.add_argument("--device", default="auto", help="auto | cuda | mps | cpu")
    p.add_argument("--dtype", default=None, help="bfloat16 | float16 | float32")
    p.add_argument("--cfg-scale", type=float, default=1.3, help="Guidance scale")
    p.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    p.add_argument("--mock", action="store_true", help="Use the mock engine (no weights)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    script_path = Path(args.script)
    if not script_path.is_file():
        logger.error("Script file not found: %s", script_path)
        return 2
    script_text = script_path.read_text(encoding="utf-8")

    paths = AppPaths.default().ensure()
    library = VoiceLibrary(paths.voices_dir, cache_dir=paths.outputs_dir / ".cache")
    library.discover()

    # Register cloned voices first so they can be assigned to speakers.
    for label, sample in _parse_kv(args.clone, "clone").items():
        if not Path(sample).is_file():
            logger.error("Clone sample not found: %s", sample)
            return 2
        library.register_cloned(sample, label=label)
        logger.info("Registered cloned voice %r from %s", label, sample)

    assignment: dict[int, str] = {}
    for label, voice in _parse_kv(args.voice, "voice").items():
        assignment[_speaker_index(label)] = voice

    cfg = GenerationConfig(
        model_id=args.model_id or GenerationConfig().model_id,
        device=None if args.device == "auto" else args.device,
        dtype=args.dtype,
        cfg_scale=args.cfg_scale,
        seed=args.seed,
    )

    mock = args.mock or force_mock_env()
    runtime = describe_runtime(cfg, mock=mock)
    logger.info(
        "Runtime: device=%s dtype=%s attn=%s mock=%s",
        runtime.device,
        runtime.dtype,
        runtime.attn_implementation,
        runtime.mock,
    )
    for note in runtime.notes:
        logger.info("Note: %s", note)

    out_path = Path(args.out) if args.out else paths.outputs_dir / timestamped_name(script_path.stem)
    engine = get_or_create_engine(cfg, mock=mock)

    try:
        result = generate(
            script_text=script_text,
            voice_assignment=assignment,
            library=library,
            cfg=cfg,
            engine=engine,
            cloned_voices=library.cloned,
            out_path=out_path,
        )
    except GenerationError as exc:
        logger.error("Invalid script/voices: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.error("Generation failed: %s", exc)
        return 1

    logger.info(
        "Done: %s (%.1fs, %d speaker(s))",
        result.out_path,
        result.duration_seconds,
        result.num_speakers,
    )
    print(result.out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
