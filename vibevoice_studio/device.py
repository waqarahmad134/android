"""Device, dtype and attention-implementation auto-detection.

``torch`` is imported lazily inside each function so this module imports cleanly
even when torch is not installed (e.g. lint/byte-compile in CI, or running the
mock engine). When torch is missing we degrade gracefully to a CPU description.
"""

from __future__ import annotations

import importlib.util

from .config import GenerationConfig, RuntimeInfo

_VALID_DEVICES = ("cuda", "mps", "cpu")


def _torch():
    """Import torch lazily; return None if it is unavailable."""
    try:
        import torch  # noqa: PLC0415

        return torch
    except Exception:  # pragma: no cover - environment without torch
        return None


def detect_device(preferred: str | None = None) -> str:
    """Pick the best available device.

    Honors ``preferred`` only if that device is actually available, otherwise
    falls back through cuda -> mps -> cpu.
    """
    torch = _torch()
    available = {"cpu"}
    if torch is not None:
        if torch.cuda.is_available():
            available.add("cuda")
        if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
            available.add("mps")

    if preferred and preferred != "auto":
        if preferred in available:
            return preferred
        # Requested device not available -> fall through to auto-detection.

    for candidate in ("cuda", "mps", "cpu"):
        if candidate in available:
            return candidate
    return "cpu"


def select_dtype(device: str, override: str | None = None):
    """Return a ``torch.dtype`` appropriate for ``device``.

    cuda -> bfloat16, cpu/mps -> float32. An explicit ``override`` string
    ("bfloat16"/"float16"/"float32") takes precedence when valid.
    """
    torch = _torch()
    if torch is None:  # pragma: no cover - environment without torch
        return override or ("bfloat16" if device == "cuda" else "float32")

    mapping = {
        "bfloat16": torch.bfloat16,
        "float16": torch.float16,
        "float32": torch.float32,
    }
    if override and override in mapping:
        return mapping[override]
    if device == "cuda":
        return torch.bfloat16
    return torch.float32


def select_attn_implementation(device: str, override: str | None = None) -> str:
    """Choose an attention backend.

    ``flash_attention_2`` is only attempted on CUDA when the ``flash_attn``
    package is importable; otherwise we fall back to ``sdpa`` (PyTorch's scaled
    dot-product attention), which works everywhere.
    """
    if override:
        return override
    if device == "cuda" and importlib.util.find_spec("flash_attn") is not None:
        return "flash_attention_2"
    return "sdpa"


def _dtype_name(dtype) -> str:
    """Human-readable dtype name, robust to plain-string fallbacks."""
    name = getattr(dtype, "__str__", lambda: str(dtype))()
    return name.replace("torch.", "")


def describe_runtime(cfg: GenerationConfig, mock: bool = False) -> RuntimeInfo:
    """Resolve and summarise the runtime for display in the UI/CLI banner."""
    if mock:
        return RuntimeInfo(
            device="system",
            dtype="n/a",
            attn_implementation="n/a",
            mock=True,
            notes=["Preview mode — offline system voice, no model weights required."],
        )

    device = detect_device(cfg.device)
    dtype = select_dtype(device, cfg.dtype)
    attn = select_attn_implementation(device, cfg.attn_implementation)
    notes: list[str] = []
    if _torch() is None:
        notes.append("PyTorch not installed — install requirements before real generation.")
    elif device == "cpu":
        notes.append("Running on CPU — generation will be slow. A CUDA GPU is recommended.")
    elif device == "mps":
        notes.append("Running on Apple Silicon (MPS) in float32.")
    return RuntimeInfo(
        device=device,
        dtype=_dtype_name(dtype),
        attn_implementation=attn,
        mock=False,
        notes=notes,
    )
