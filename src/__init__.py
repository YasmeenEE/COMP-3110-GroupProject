"""
LHDiff tracks lines between versions of a file.

    Step 1: src.preprocessing
    Step 2: src.detect_unchanged
    Steps 3 & 4: src.match_candidates (content + context similarity)

Public API imports:
    normalize, preprocess                         -- Step 1
    detect_unchanged, Step2Result                 -- Step 2
    extract_context                               -- context windows
    calculate_content_similarity                  -- content score
    calculate_context_similarity                  -- context score
    match_changed_lines, combined_similarity      -- Steps 3 & 4
"""

from .preprocessing import normalize, preprocess
from .detect_unchanged import detect_unchanged, Step2Result
from .context_extractor import extract_context
from .similarity import calculate_content_similarity
from .context_similarity import calculate_context_similarity
from .match_candidates import match_changed_lines, combined_similarity

__all__ = [
    "normalize",
    "preprocess",
    "detect_unchanged",
    "Step2Result",
    "extract_context",
    "calculate_content_similarity",
    "calculate_context_similarity",
    "match_changed_lines",
    "combined_similarity",
]

__version__ = "0.3.0"  # implemented through Steps 3 & 4
