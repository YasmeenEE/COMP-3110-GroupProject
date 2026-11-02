"""
Step 1: Preprocessing; cleaning up lines before comparing them.

Make everything lowercase, replace extra whitespace with a single space,
and remove spaces at the start and end. This keeps changes in case or
indentation from getting in the way.

For example:
    "    FileReader fr = new FileReader(path);" -> "filereader fr = new filereader(path);"
"""

from __future__ import annotations

import re

_WS_RE = re.compile(r"\s+")


def normalize(line: str) -> str:
    """Normalise a single line (Step 1)."""
    line = line.lower()            # 1. case fold
    line = _WS_RE.sub(" ", line)   # 2. collapse internal whitespace
    return line.strip()            # 3. trim ends


def preprocess(lines: list[str]) -> list[str]:
    """Apply Step 1 to every line of a file (given as a list of raw lines)."""
    return [normalize(line) for line in lines]
