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
        import torch  # noqa: PLC0415
        from vibevoice.modular.modeling_vibevoice_inference import (  # noqa: PLC0415
            VibeVoiceForConditionalGenerationInference,
        )
        from vibevoice.processor.vibevoice_processor import (  # noqa: PLC0415
            VibeVoiceProcessor,
        )

        self.device = detect_device(self.cfg.device)
        dtype = select_dtype(self.device, self.cfg.dtype)
        attn = select_attn_implementation(self.device, self.cfg.attn_implementation)

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

        sample_paths = [str(p) for p in voice_sample_paths]
        inputs = self.processor(
            text=[engine_text],
            voice_samples=[sample_paths],
            padding=True,
            return_tensors="pt",
        )
        if self.device and self.device != "cpu":
            inputs = {
                k: (v.to(self.device) if hasattr(v, "to") else v) for k, v in dict(inputs).items()
            }

        gen_kwargs = {"cfg_scale": cfg.cfg_scale, "tokenizer": self.processor.tokenizer}
        if cfg.max_new_tokens:
            gen_kwargs["max_new_tokens"] = cfg.max_new_tokens

        with torch.no_grad():
            outputs = self.model.generate(**inputs, **gen_kwargs)

        audio = self._extract_audio(outputs)
        return audio, SAMPLE_RATE

    @staticmethod
    def _extract_audio(outputs):
        """Pull a 1-D numpy waveform out of the model's generate() result."""
        import numpy as np  # noqa: PLC0415

        candidate = outputs
        for attr in ("speech_outputs", "audios", "audio", "waveform"):
            if hasattr(candidate, attr):
                candidate = getattr(candidate, attr)
                break

        if isinstance(candidate, (list, tuple)):
            candidate = candidate[0]
        if hasattr(candidate, "detach"):
            candidate = candidate.detach().to("cpu").float().numpy()
        candidate = np.asarray(candidate, dtype="float32").reshape(-1)
        return candidate


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


def force_mock_env() -> bool:
    """True when the ``VIBEVOICE_MOCK`` env var requests the mock engine."""
    return os.environ.get(MOCK_ENV_VAR, "").strip().lower() in {"1", "true", "yes"}


def make_engine(cfg: GenerationConfig, mock: bool = False) -> GenerationEngine:
    """Return a :class:`MockEngine` when requested/forced, else the real engine."""
    if mock or force_mock_env():
        logger.info("Using MockEngine (no model weights required).")
        return MockEngine(cfg)
    return VibeVoiceEngine(cfg)
