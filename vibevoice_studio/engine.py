"""Generation engines.

This is the single weight-dependent surface of the project. :class:`VibeVoiceEngine`
wraps the real model; :class:`MockEngine` produces a deterministic placeholder
waveform with zero dependencies so the entire UI/CLI/test pipeline runs without
the multi-gigabyte weights. ``make_engine`` selects between them, honoring the
``VIBEVOICE_MOCK`` environment variable.
"""

from __future__ import annotations

import math
import os
from abc import ABC, abstractmethod
from pathlib import Path

from .config import MOCK_ENV_VAR, SAMPLE_RATE, GenerationConfig
from .device import detect_device, select_attn_implementation, select_dtype
from .utils import setup_logging

logger = setup_logging()


class GenerationEngine(ABC):
    """Abstract speech-synthesis backend."""

    def __init__(self, cfg: GenerationConfig):
        self.cfg = cfg

    @property
    @abstractmethod
    def is_loaded(self) -> bool: ...

    @abstractmethod
    def load(self) -> None: ...

    @abstractmethod
    def synthesize(
        self,
        engine_text: str,
        voice_sample_paths: list[Path],
        cfg: GenerationConfig,
    ) -> tuple[object, int]:
        """Return ``(audio, sample_rate)`` where ``audio`` is a 1-D float array."""


class VibeVoiceEngine(GenerationEngine):
    """The real engine backed by VibeVoice-1.5B.

    All heavy imports happen inside :meth:`load` so merely constructing the
    engine (or importing this module) never requires torch/vibevoice.
    """

    def __init__(self, cfg: GenerationConfig):
        super().__init__(cfg)
        self.model = None
        self.processor = None
        self.device: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self.model is not None and self.processor is not None

    def load(self) -> None:
        try:
            import torch  # noqa: PLC0415
            from vibevoice.modular.modeling_vibevoice_inference import (  # noqa: PLC0415
                VibeVoiceForConditionalGenerationInference,
            )
            from vibevoice.processor.vibevoice_processor import (  # noqa: PLC0415
                VibeVoiceProcessor,
            )
        except ImportError as exc:
            raise RuntimeError(
                "The real VibeVoice model is not installed, so only mock-mode "
                "(placeholder beep) audio is available. Install it with:\n"
                "  pip install -r requirements.txt\n"
                '  pip install "vibevoice @ git+https://github.com/vibevoice-community/VibeVoice"\n'
                "then run again without mock mode."
            ) from exc

        self.device = detect_device(self.cfg.device)
        dtype = select_dtype(self.device, self.cfg.dtype)
        attn = select_attn_implementation(self.device, self.cfg.attn_implementation)

        if self.device == "mps":
            # Some model ops are not yet implemented on Apple's Metal backend;
            # let PyTorch fall back to CPU for those instead of crashing.
            os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

        logger.info(
            "Loading %s on %s (dtype=%s, attn=%s)...",
            self.cfg.model_id,
            self.device,
            dtype,
            attn,
        )

        self.processor = VibeVoiceProcessor.from_pretrained(self.cfg.model_id)
        try:
            self.model = VibeVoiceForConditionalGenerationInference.from_pretrained(
                self.cfg.model_id,
                torch_dtype=dtype,
                device_map=self.device if self.device != "mps" else None,
                attn_implementation=attn,
                low_cpu_mem_usage=True,
            )
        except Exception:
            # flash-attn or device_map can fail on some setups; retry with sdpa.
            logger.warning("Primary load failed; retrying with attn=sdpa and no device_map.")
            self.model = VibeVoiceForConditionalGenerationInference.from_pretrained(
                self.cfg.model_id,
                torch_dtype=dtype,
                attn_implementation="sdpa",
                low_cpu_mem_usage=True,
            )

        if self.device == "mps":
            self.model.to("mps")
        self.model.eval()
        self._torch = torch

    def synthesize(self, engine_text, voice_sample_paths, cfg):
        import torch  # noqa: PLC0415

        if not self.is_loaded:
            self.load()

        if cfg.seed is not None:
            torch.manual_seed(cfg.seed)

        # Normalise curly apostrophes like the official demo does.
        engine_text = engine_text.replace("’", "'")
        sample_paths = [str(p) for p in voice_sample_paths]
        inputs = self.processor(
            text=[engine_text],
            voice_samples=[sample_paths],
            padding=True,
            return_tensors="pt",
            return_attention_mask=True,
        )
        # Move every tensor to the target device (mirrors demo/inference_from_file.py).
        if self.device and self.device != "cpu":
            for key, value in dict(inputs).items():
                if torch.is_tensor(value):
                    inputs[key] = value.to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=cfg.max_new_tokens,
                cfg_scale=cfg.cfg_scale,
                tokenizer=self.processor.tokenizer,
                generation_config={"do_sample": False},
                verbose=False,
            )

        audio = self._extract_audio(outputs)
        return audio, SAMPLE_RATE

    @staticmethod
    def _extract_audio(outputs):
        """Pull a 1-D numpy waveform out of the model's generate() result.

        The model returns ``outputs.speech_outputs`` (a list with one waveform
        tensor per batch item); we use the first item, as the official demo does.
        """
        import numpy as np  # noqa: PLC0415

        candidate = getattr(outputs, "speech_outputs", outputs)
        if isinstance(candidate, (list, tuple)):
            candidate = candidate[0]
        if hasattr(candidate, "detach"):
            candidate = candidate.detach().to("cpu").float().numpy()
        return np.asarray(candidate, dtype="float32").reshape(-1)


class MockEngine(GenerationEngine):
    """A dependency-free placeholder that fabricates a short waveform.

    The output length scales with the script length so UI/CLI/test flows produce
    a real, playable WAV without any model weights. A distinct sine tone per
    speaker makes multi-speaker mapping audible during development.
    """

    _loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        self._loaded = True

    def synthesize(self, engine_text, voice_sample_paths, cfg):
        import numpy as np  # noqa: PLC0415

        self.load()
        # ~0.06s of audio per character, clamped to a sane range.
        seconds = max(1.0, min(60.0, len(engine_text) * 0.06))
        n = int(seconds * SAMPLE_RATE)
        t = np.linspace(0.0, seconds, n, endpoint=False, dtype="float32")

        num_speakers = max(1, len(voice_sample_paths))
        audio = np.zeros(n, dtype="float32")
        for i in range(num_speakers):
            freq = 180.0 + 70.0 * i  # distinct tone per speaker
            audio += 0.2 * np.sin(2.0 * math.pi * freq * t).astype("float32")
        audio /= num_speakers
        return audio, SAMPLE_RATE


def _render_with_pyttsx3(engine_text: str):
    """Speak the script with the OS's built-in offline voice via pyttsx3.

    Returns a 1-D float32 numpy waveform at ``SAMPLE_RATE``, or ``None`` if
    pyttsx3 / a system speech engine is unavailable. Each speaker gets a
    different system voice when more than one is installed, and the ``Speaker N:``
    labels are stripped so they are not read aloud.
    """
    try:
        import tempfile  # noqa: PLC0415

        import numpy as np  # noqa: PLC0415
        import pyttsx3  # noqa: PLC0415

        from .script_parser import parse_script  # noqa: PLC0415
        from .utils import load_and_normalize_audio  # noqa: PLC0415
    except Exception:
        return None

    try:
        engine = pyttsx3.init()
    except Exception:
        return None

    voices = []
    try:
        voices = engine.getProperty("voices") or []
    except Exception:
        voices = []

    parsed = parse_script(engine_text)
    segments = []
    gap = np.zeros(int(0.25 * SAMPLE_RATE), dtype="float32")  # pause between turns

    try:
        with tempfile.TemporaryDirectory() as tmp:
            for idx, line in enumerate(parsed.lines):
                if not line.text:
                    continue
                if voices:
                    voice = voices[(line.speaker_index - 1) % len(voices)]
                    try:
                        engine.setProperty("voice", voice.id)
                    except Exception:
                        pass
                wav_path = os.path.join(tmp, f"seg_{idx}.wav")
                engine.save_to_file(line.text, wav_path)
                engine.runAndWait()
                if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
                    return None
                seg = load_and_normalize_audio(wav_path, target_sr=SAMPLE_RATE)
                segments.append(np.asarray(seg, dtype="float32"))
                segments.append(gap)
    except Exception:
        return None

    if not segments:
        return None
    return np.concatenate(segments).astype("float32")


class PreviewEngine(GenerationEngine):
    """Fast, offline preview using the operating system's built-in voice.

    Unlike the real :class:`VibeVoiceEngine`, this does **not** clone your voice
    samples — it just speaks the actual words of the script with a generic system
    voice. It needs no model weights and is instant, which makes it ideal for
    drafting a script before committing to a full VibeVoice render. If no system
    speech engine is available it falls back to :class:`MockEngine`'s tone.
    """

    _loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        self._loaded = True

    def synthesize(self, engine_text, voice_sample_paths, cfg):
        self.load()
        audio = _render_with_pyttsx3(engine_text)
        if audio is not None and len(audio) > 0:
            return audio, SAMPLE_RATE
        logger.warning(
            "No system speech engine available (install pyttsx3 + an OS voice); "
            "falling back to a placeholder tone."
        )
        return MockEngine(self.cfg).synthesize(engine_text, voice_sample_paths, cfg)


def force_mock_env() -> bool:
    """True when the ``VIBEVOICE_MOCK`` env var requests the mock engine."""
    return os.environ.get(MOCK_ENV_VAR, "").strip().lower() in {"1", "true", "yes"}


def model_available() -> bool:
    """True if torch and the vibevoice package are importable (real mode possible)."""
    import importlib.util  # noqa: PLC0415

    return all(
        importlib.util.find_spec(name) is not None
        for name in ("torch", "vibevoice")
    )


def make_engine(cfg: GenerationConfig, mock: bool = False) -> GenerationEngine:
    """Return a :class:`PreviewEngine` when mock/preview is requested, else real."""
    if mock or force_mock_env():
        logger.info("Using PreviewEngine (offline system voice, no model weights).")
        return PreviewEngine(cfg)
    return VibeVoiceEngine(cfg)
