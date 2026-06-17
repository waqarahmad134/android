# 🎙️ VibeVoice Studio

A **local, no-API** podcast & story audio generator powered by Microsoft's
open-source **[VibeVoice-1.5B](https://github.com/vibevoice-community/VibeVoice)**
text-to-speech model. Write a multi-speaker script, pick voices (or **clone your
own**), and generate long-form audio — up to ~90 minutes and 4 speakers —
entirely on **your own hardware**.

- 🧠 Runs the open VibeVoice-1.5B model locally — **no API keys, no cloud, no per-minute billing**
- 🗣️ Up to **4 speakers** with a simple `Speaker 1:` / `Speaker 2:` script format
- 🎤 **Voice cloning** from a 10–30s sample (use your own voice)
- 🖥️ Auto-detects **NVIDIA GPU (CUDA)**, **Apple Silicon (MPS)**, or **CPU**
- 🌐 **Gradio web UI** + a scriptable **CLI**
- 🧪 **Mock mode** so you can try the whole interface with zero model weights

---

## Quick start

```bash
# 1. Create an environment
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install the VibeVoice model package (community fork; Microsoft removed the original)
pip install "vibevoice @ git+https://github.com/vibevoice-community/VibeVoice"

# 4. (Optional) pre-download the weights — otherwise they download on first run
huggingface-cli download vibevoice/VibeVoice-1.5B

# 5. (Optional) create placeholder voices so the menus aren't empty on first run
python scripts/make_demo_voices.py
```

> **Mock mode = a beep, not speech.** `VIBEVOICE_MOCK=1 python app.py` (or
> `python app.py --mock`) launches the full UI with a mock engine that outputs a
> **placeholder tone** — useful to verify the workflow before downloading the
> weights. For **real voices**, install the model (steps 3–4), make sure mock is
> off (`unset VIBEVOICE_MOCK`), and run `python app.py` with **no** `--mock`. The
> banner at the top of the UI shows `mock: True/False`.
>
> The placeholder voices from step 5 are synthetic tones — **replace them with
> real 10–30s speech samples** in `assets/voices/` for actual generation.

---

## Usage — Web UI

```bash
python app.py                 # open the printed http://127.0.0.1:7860 URL
python app.py --share         # public Gradio link
python app.py --mock          # no weights needed (placeholder audio)
```

In the UI: paste/load a script → assign a voice to each speaker → (optionally)
upload or record a sample under **Clone a voice** → **Generate** → play and
download the WAV.

## Usage — CLI

```bash
python cli.py \
  --script assets/text_examples/1_podcast_2p.txt \
  --voice "Speaker 1=Alice" \
  --voice "Speaker 2=Carter" \
  --out outputs/episode1.wav
```

Clone a voice and assign it to a speaker:

```bash
python cli.py \
  --script assets/text_examples/2_story_4p.txt \
  --clone "MyVoice=/path/to/sample.wav" \
  --voice "Speaker 1=MyVoice" \
  --voice "Speaker 2=Alice" \
  --out outputs/story.wav
```

Useful flags: `--device {auto,cuda,mps,cpu}`, `--dtype {bfloat16,float16,float32}`,
`--cfg-scale 1.3`, `--seed 42`, `--mock`.

---

## Script format

Each turn begins with a 1-based `Speaker N:` label. Turns may span multiple
lines; continuation lines are merged into the current speaker.

```
Speaker 1: Welcome to the show.
Speaker 2: Thanks for having me. I have a lot
to share today.
Speaker 1: Let's dive in.
```

Up to **4 speakers**; numbers should be contiguous starting at 1.

## Voices

Drop reference `*.wav` files into `assets/voices/` (see
[`assets/voices/README.md`](assets/voices/README.md) for the naming convention)
and they appear in the voice menus automatically. Runtime voice cloning uses the
same mechanism for a single session.

---

## Hardware notes

| Device | dtype | Notes |
| --- | --- | --- |
| NVIDIA GPU (CUDA) | bfloat16 | Recommended. ~8GB VRAM ideal for 1.5B. Uses `flash_attention_2` when `flash-attn` is installed, otherwise `sdpa`. |
| Apple Silicon (MPS) | float32 | Works; slower than CUDA. |
| CPU | float32 | Works but **slow** for long scripts. |

Device, dtype and attention backend are auto-detected (override with
`--device` / advanced settings) and shown in the UI banner and CLI logs.

---

## Project layout

```
vibevoice_studio/      core engine package (all real logic)
  config.py            constants & dataclasses (dependency-free)
  device.py            device / dtype / attention auto-detection
  script_parser.py     multi-speaker script parsing & validation
  voices.py            preset + cloned voice management
  engine.py            VibeVoiceEngine (real) + MockEngine (no weights)
  generate.py          the single generate() shared by UI and CLI
  utils.py             audio I/O & helpers
app.py                 Gradio web UI (thin)
cli.py                 command-line interface (thin)
assets/voices/         preset voice samples
assets/text_examples/  example scripts
outputs/               generated WAVs (gitignored)
tests/                 unit + mock end-to-end tests
```

## Development

```bash
pip install -e ".[dev]"
ruff check .
python -m compileall vibevoice_studio app.py cli.py tests
pytest                                  # runs without model weights
python scripts/make_demo_voices.py      # placeholder voices for a quick smoke test
VIBEVOICE_MOCK=1 python cli.py --script assets/text_examples/1_podcast_2p.txt \
  --voice "Speaker 1=Alice" --voice "Speaker 2=Carter" --out outputs/test.wav
```

## License

MIT (this wrapper). The VibeVoice model and its inference code are distributed
under their own terms — see the
[community fork](https://github.com/vibevoice-community/VibeVoice).
