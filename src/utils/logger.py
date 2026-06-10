"""Lightweight, consistently-formatted logging."""
from __future__ import annotations

import logging
import os
import sys

_CONFIGURED = False


def configure_logging(level: str = "INFO", file: str | None = None) -> None:
    """Configure root logging once. Safe to call repeatedly."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if file:
        os.makedirs(os.path.dirname(file) or ".", exist_ok=True)
        handlers.append(logging.FileHandler(file))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
