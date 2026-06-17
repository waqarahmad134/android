#!/usr/bin/env python3
"""Gradio web UI for VibeVoice Studio.

A thin front-end: it collects a script, per-speaker voice assignments and an
optional cloned voice, then delegates to ``vibevoice_studio.generate.generate``.
Run with ``python app.py`` (add ``--mock`` to try the interface without weights).
"""

from __future__ import annotations

import argparse

from vibevoice_studio.config import MAX_SPEAKERS, AppPaths, GenerationConfig
from vibevoice_studio.device import describe_runtime
from vibevoice_studio.engine import force_mock_env, model_available
from vibevoice_studio.generate import (
    GenerationError,
    generate,
    get_or_create_engine,
)
from vibevoice_studio.script_parser import parse_script
from vibevoice_studio.utils import setup_logging, timestamped_name
from vibevoice_studio.voices import VoiceLibrary

logger = setup_logging()

EXAMPLE_SCRIPT = (
    "Speaker 1: Welcome to VibeVoice Studio, the local podcast generator.\n"
    "Speaker 2: Thanks for having me! I love that this runs entirely on my own machine.\n"
    "Speaker 1: No API keys, no cloud — just your hardware and an open model.\n"
    "Speaker 2: Let's make something great."
)


def _runtime_banner(cfg: GenerationConfig, mock: bool) -> str:
    rt = describe_runtime(cfg, mock=mock)
    lines = [
        f"**Device:** `{rt.device}` &nbsp;·&nbsp; **dtype:** `{rt.dtype}` "
        f"&nbsp;·&nbsp; **attention:** `{rt.attn_implementation}` "
        f"&nbsp;·&nbsp; **mock:** `{rt.mock}`"
    ]
    if rt.mock:
        lines.append(
            "### 🔊 Preview mode — real words spoken by your **system voice** "
            "(instant, offline, but *not* your cloned voice).\n"
            "Uncheck **Preview mode** under *Advanced settings* for full VibeVoice "
            "quality with voice cloning (the model must be installed — see the README)."
        )
    elif not model_available():
        lines.append(
            "### ⚠️ Real mode selected, but the VibeVoice model is **not installed**.\n"
            "Install it, then generate:\n"
            "```\npip install -r requirements.txt\n"
            'pip install "vibevoice @ git+https://github.com/vibevoice-community/VibeVoice"\n```'
        )
    lines += [f"> {note}" for note in rt.notes]
    return "\n\n".join(lines)


def _example_choices(paths: AppPaths) -> dict[str, str]:
    out: dict[str, str] = {}
    if paths.examples_dir.is_dir():
        for txt in sorted(paths.examples_dir.glob("*.txt")):
            out[txt.stem] = txt.read_text(encoding="utf-8")
    return out


def build_demo(mock: bool = False):
    import gradio as gr  # imported lazily so the module stays importable without gradio

    paths = AppPaths.default().ensure()
    library = VoiceLibrary(paths.voices_dir, cache_dir=paths.outputs_dir / ".cache")
    library.discover()
    base_cfg = GenerationConfig()
    examples = _example_choices(paths)

    def voice_choices() -> list[str]:
        return library.names()

    with gr.Blocks(title="VibeVoice Studio") as demo:
        gr.Markdown("# 🎙️ VibeVoice Studio\nLocal, no-API podcast & story generator powered by VibeVoice-1.5B.")
        banner = gr.Markdown(_runtime_banner(base_cfg, mock))

        with gr.Row():
            with gr.Column(scale=3):
                script = gr.Textbox(
                    label="Script (use 'Speaker 1:', 'Speaker 2:' …)",
                    value=EXAMPLE_SCRIPT,
                    lines=14,
                )
                with gr.Row():
                    example_dd = gr.Dropdown(
                        label="Load example",
                        choices=list(examples.keys()),
                        value=None,
                    )

                gr.Markdown("### Voice assignment")
                speaker_dropdowns = []
                for i in range(1, MAX_SPEAKERS + 1):
                    dd = gr.Dropdown(
                        label=f"Speaker {i}",
                        choices=voice_choices(),
                        value=(voice_choices()[i - 1] if len(voice_choices()) >= i else None),
                        interactive=True,
                    )
                    speaker_dropdowns.append(dd)

                with gr.Accordion("Clone a voice (use your own)", open=False):
                    clone_audio = gr.Audio(
                        label="Voice sample (10–30s of clean speech)",
                        sources=["upload", "microphone"],
                        type="filepath",
                    )
                    clone_label = gr.Textbox(label="Name for this voice", value="My Voice")
                    add_clone_btn = gr.Button("Add cloned voice")

                with gr.Accordion("Advanced settings", open=False):
                    mock_toggle = gr.Checkbox(
                        label="Preview mode (instant offline system voice — no model weights, no cloning)",
                        value=mock,
                    )
                    device_dd = gr.Dropdown(
                        label="Device", choices=["auto", "cuda", "mps", "cpu"], value="auto"
                    )
                    cfg_scale = gr.Slider(
                        label="Guidance (cfg_scale)", minimum=1.0, maximum=2.5, value=1.3, step=0.05
                    )
                    seed = gr.Number(label="Seed (blank = random)", value=None, precision=0)

                generate_btn = gr.Button("🎧 Generate", variant="primary")

            with gr.Column(scale=2):
                audio_out = gr.Audio(label="Generated audio", type="filepath")
                file_out = gr.File(label="Download WAV")
                status = gr.Markdown()

        # -- callbacks -------------------------------------------------------

        def on_load_example(name):
            return examples.get(name, "")

        example_dd.change(on_load_example, inputs=example_dd, outputs=script)

        def on_toggle_mock(mock_on, device):
            cfg = GenerationConfig(device=None if device == "auto" else device)
            return _runtime_banner(cfg, bool(mock_on))

        mock_toggle.change(on_toggle_mock, inputs=[mock_toggle, device_dd], outputs=banner)
        device_dd.change(on_toggle_mock, inputs=[mock_toggle, device_dd], outputs=banner)

        def on_add_clone(audio_path, label):
            if not audio_path:
                return [gr.update() for _ in speaker_dropdowns] + ["⚠️ Upload or record a sample first."]
            label = (label or "My Voice").strip()
            library.register_cloned(audio_path, label=label)
            choices = voice_choices()
            updates = [gr.update(choices=choices) for _ in speaker_dropdowns]
            return updates + [f"✅ Added cloned voice **{label}**. Assign it to a speaker."]

        add_clone_btn.click(
            on_add_clone,
            inputs=[clone_audio, clone_label],
            outputs=speaker_dropdowns + [status],
        )

        def on_generate(script_text, v1, v2, v3, v4, device, cfg_scale_val, seed_val, mock_on, progress=gr.Progress()):  # noqa: B008
            assignment_all = {1: v1, 2: v2, 3: v3, 4: v4}
            parsed = parse_script(script_text)
            assignment = {
                idx: assignment_all.get(idx) for idx in parsed.speaker_indices
            }
            cfg = GenerationConfig(
                device=None if device == "auto" else device,
                cfg_scale=float(cfg_scale_val),
                seed=int(seed_val) if seed_val not in (None, "") else None,
            )
            out_path = paths.outputs_dir / timestamped_name("podcast")
            engine = get_or_create_engine(cfg, mock=bool(mock_on))
            try:
                progress(0.1, desc="Preparing…")
                result = generate(
                    script_text=script_text,
                    voice_assignment=assignment,
                    library=library,
                    cfg=cfg,
                    engine=engine,
                    cloned_voices=library.cloned,
                    out_path=out_path,
                )
                progress(1.0, desc="Done")
            except GenerationError as exc:
                return None, None, f"❌ **Invalid script:** {exc}"
            except Exception as exc:  # noqa: BLE001
                return None, None, f"❌ **Generation failed:** {exc}"

            msg = (
                f"✅ Generated **{result.duration_seconds:.1f}s** of audio for "
                f"**{result.num_speakers}** speaker(s)."
            )
            return str(result.out_path), str(result.out_path), msg

        generate_btn.click(
            on_generate,
            inputs=[script, *speaker_dropdowns, device_dd, cfg_scale, seed, mock_toggle],
            outputs=[audio_out, file_out, status],
        )

    return demo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VibeVoice Studio web UI")
    parser.add_argument("--mock", action="store_true", help="Use the mock engine (no weights)")
    parser.add_argument("--share", action="store_true", help="Create a public Gradio share link")
    parser.add_argument("--port", type=int, default=7860, help="Port to serve on")
    args = parser.parse_args(argv)

    demo = build_demo(mock=args.mock or force_mock_env())
    demo.launch(server_port=args.port, share=args.share)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
