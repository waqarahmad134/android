"""Parsing and validation of multi-speaker scripts.

The script format mirrors VibeVoice's own convention: each turn starts with a
``Speaker N:`` label, where ``N`` is 1-based. A turn may span multiple lines —
continuation lines (those without a new ``Speaker N:`` prefix) are appended to
the current speaker's text.

Example::

    Speaker 1: Welcome to the show.
    Speaker 2: Thanks for having me. I have a lot
    to share today.
    Speaker 1: Let's dive in.

This module is pure standard-library Python and is the most heavily unit-tested
part of the project.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .config import MAX_SPEAKERS

# Matches "Speaker 1:", "  speaker 02 :", etc. Capturing the index and the rest.
_SPEAKER_RE = re.compile(r"^\s*[Ss]peaker\s+(\d+)\s*:\s*(.*)$")


@dataclass
class ScriptLine:
    """A single speaker turn."""

    speaker_index: int  # 1-based as written by the user
    text: str


@dataclass
class ParsedScript:
    """The structured result of :func:`parse_script`."""

    lines: list[ScriptLine]
    speaker_indices: list[int]  # sorted, unique, e.g. [1, 2]

    def num_speakers(self) -> int:
        return len(self.speaker_indices)

    def to_engine_text(self) -> str:
        """Re-emit a normalized script that the VibeVoice processor expects."""
        return "\n".join(f"Speaker {ln.speaker_index}: {ln.text}".rstrip() for ln in self.lines)


def parse_script(raw: str) -> ParsedScript:
    """Parse a raw multi-speaker script into a :class:`ParsedScript`.

    Blank lines are ignored. Continuation lines are merged into the preceding
    turn. Leading text before any ``Speaker N:`` label is implicitly attributed
    to ``Speaker 1`` so a plain block of prose still works for single-speaker
    narration.
    """
    lines: list[ScriptLine] = []
    current: ScriptLine | None = None

    for rawline in raw.splitlines():
        line = rawline.strip()
        if not line:
            continue
        match = _SPEAKER_RE.match(line)
        if match:
            index = int(match.group(1))
            text = match.group(2).strip()
            current = ScriptLine(speaker_index=index, text=text)
            lines.append(current)
        elif current is not None:
            # Continuation of the previous turn.
            current.text = f"{current.text} {line}".strip()
        else:
            # Prose before any speaker label -> attribute to Speaker 1.
            current = ScriptLine(speaker_index=1, text=line)
            lines.append(current)

    speaker_indices = sorted({ln.speaker_index for ln in lines})
    return ParsedScript(lines=lines, speaker_indices=speaker_indices)


def validate_script(parsed: ParsedScript, max_speakers: int = MAX_SPEAKERS) -> list[str]:
    """Return a list of human-readable problems; empty means the script is valid."""
    errors: list[str] = []

    if not parsed.lines:
        errors.append("The script is empty. Add at least one 'Speaker N: ...' line.")
        return errors

    if any(not ln.text for ln in parsed.lines):
        errors.append("One or more speaker turns have no text.")

    for index in parsed.speaker_indices:
        if index < 1:
            errors.append(f"Speaker numbers must start at 1 (found Speaker {index}).")

    if parsed.num_speakers() > max_speakers:
        errors.append(
            f"VibeVoice supports up to {max_speakers} speakers, "
            f"but the script uses {parsed.num_speakers()}."
        )

    # Warn about non-contiguous numbering, e.g. using Speaker 3 without Speaker 2.
    positive = [i for i in parsed.speaker_indices if i >= 1]
    if positive:
        expected = list(range(1, len(positive) + 1))
        if positive != expected:
            errors.append(
                "Speaker numbers should be contiguous starting at 1 "
                f"(found {positive}, expected {expected})."
            )

    return errors
