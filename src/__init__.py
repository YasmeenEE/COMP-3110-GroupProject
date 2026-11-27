"""
LHDiff tracks lines between versions of a file.

    Step 1: src.preprocessing
    Step 2: src.detect_unchanged
    Step 3: src.generate_candidates (SimHash + Hamming, top k=15)
    Step 4: src.match_candidates (textual similarity on candidates)
    Step 5: src.detect_line_split (line splits)

Public API imports:
    normalize, preprocess                         -- Step 1
    detect_unchanged, Step2Result                 -- Step 2
    extract_context                               -- context windows
    simhash, hamming_distance, hamming_similarity -- SimHash primitives
    generate_candidates, Candidate, ...           -- Step 3
    calculate_content_similarity                  -- content score (Step 4)
    calculate_context_similarity                  -- context score (Step 4)
    match_changed_lines, combined_similarity      -- Step 4
    detect_line_splits, SPLIT_THRESHOLD           -- Step 5
"""

from .preprocessing import normalize, preprocess
from .detect_unchanged import detect_unchanged, Step2Result
from .context_extractor import extract_context
from .simhash_util import simhash, hamming_distance, hamming_similarity, SIMHASH_BITS
from .generate_candidates import (
    generate_candidates,
    Candidate,
    CandidateListResult,
    CANDIDATE_K,
)
from .resolve_conflicts import (
    calculate_text_similarity,
    calculate_context_similarity,
    combined_similarity,
    resolve_conflicts,
)
from .detect_line_split import detect_line_splits, SPLIT_THRESHOLD

__all__ = [
    "normalize",
    "preprocess",
    "detect_unchanged",
    "Step2Result",
    "extract_context",
    "simhash",
    "hamming_distance",
    "hamming_similarity",
    "SIMHASH_BITS",
    "generate_candidates",
    "Candidate",
    "CandidateListResult",
    "CANDIDATE_K",
    "calculate_text_similarity",
    "calculate_context_similarity",
    "resolve_conflicts",
    "combined_similarity",
    "detect_line_splits",
    "SPLIT_THRESHOLD",
]

__version__ = "0.5.0"  # Step 5 line split detection
