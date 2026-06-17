"""VibeVoice Studio — a local, no-API podcast & story audio generator.

This package wraps Microsoft's open-source VibeVoice-1.5B text-to-speech model
to turn multi-speaker scripts into long-form audio on your own hardware. All of
the real logic lives here so that the Gradio web UI (``app.py``) and the command
line tool (``cli.py``) are thin shells over the same :func:`generate` function.

Heavy machine-learning dependencies (``torch``, ``vibevoice``) are imported
lazily so that importing this package — and running the test suite or the mock
engine — never requires the model weights to be present.
"""

from .config import (
    DEFAULT_MODEL_ID,
    MAX_SPEAKERS,
    SAMPLE_RATE,
    AppPaths,
    GenerationConfig,
)
from .generate import GenerateResult, generate

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_MODEL_ID",
    "MAX_SPEAKERS",
    "SAMPLE_RATE",
    "AppPaths",
    "GenerationConfig",
    "GenerateResult",
    "generate",
    "__version__",
]
