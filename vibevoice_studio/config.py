"""Configuration data structures and constants.

This module is intentionally dependency-free (only the standard library) so it
can always be imported, even in environments without ``torch`` or the model
weights.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: HuggingFace repo id for the default model. Microsoft removed the original
#: ``microsoft/VibeVoice-1.5B`` repo; the community fork mirrors the weights.
DEFAULT_MODEL_ID = "vibevoice/VibeVoice-1.5B"

#: VibeVoice supports up to four distinct speakers in a single generation.
MAX_SPEAKERS = 4

#: Output sample rate of the VibeVoice acoustic decoder (Hz).
SAMPLE_RATE = 24000

#: Default classifier-free-guidance scale used during generation.
DEFAULT_CFG_SCALE = 1.3

#: Environment variable that forces the mock engine (no weights required).
MOCK_ENV_VAR = "VIBEVOICE_MOCK"


@dataclass
class GenerationConfig:
    """Tunable settings shared by the UI and CLI.

    ``device``, ``dtype`` and ``attn_implementation`` default to ``None`` which
    means "auto-detect" — see :mod:`vibevoice_studio.device`.
    """

    model_id: str = DEFAULT_MODEL_ID
    device: str | None = None  # None -> auto ("cuda" | "mps" | "cpu")
    dtype: str | None = None  # None -> auto ("bfloat16" | "float32" | "float16")
    attn_implementation: str | None = None  # None -> auto
    cfg_scale: float = DEFAULT_CFG_SCALE
    seed: int | None = None
    max_new_tokens: int | None = None


@dataclass
class AppPaths:
    """Filesystem locations used by the application."""

    voices_dir: Path
    examples_dir: Path
    outputs_dir: Path

    @classmethod
    def default(cls, root: Path | None = None) -> AppPaths:
        """Return the standard project layout rooted at the repo directory."""
        base = root or Path(__file__).resolve().parent.parent
        return cls(
            voices_dir=base / "assets" / "voices",
            examples_dir=base / "assets" / "text_examples",
            outputs_dir=base / "outputs",
        )

    def ensure(self) -> AppPaths:
        """Create the output directories if they do not yet exist."""
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        (self.outputs_dir / ".cache").mkdir(parents=True, exist_ok=True)
        return self


@dataclass
class RuntimeInfo:
    """Resolved runtime details, surfaced in the UI banner and CLI output."""

    device: str
    dtype: str
    attn_implementation: str
    mock: bool = False
    notes: list[str] = field(default_factory=list)
