"""
Step 1 -- Preprocessing.

Each line of a source file is normalised so that later comparison is robust to
re-indentation and case-only edits, while staying completely language
independent. Normalisation:

    1. lowercase the line
    2. collapse every run of whitespace to a single space
    3. strip leading / trailing whitespace

Example (from the slides' "After Preprocessing" column):
    "    FileReader fr = new FileReader(path);"
      -> "filereader fr = new filereader(path);"
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
