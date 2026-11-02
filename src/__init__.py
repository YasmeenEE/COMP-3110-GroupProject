"""
LHDiff -- a language-independent hybrid line-tracking technique.

This package implements the first two steps of LHDiff:

    Step 1  preprocessing     (src.preprocessing)
    Step 2  detect unchanged  (src.detect_unchanged)

Public API:
    normalize, preprocess            -- Step 1
    detect_unchanged, Step2Result    -- Step 2
"""

from .preprocessing import normalize, preprocess
from .detect_unchanged import detect_unchanged, Step2Result

__all__ = [
    "normalize",
    "preprocess",
    "detect_unchanged",
    "Step2Result",
]

__version__ = "0.2.0"  # implemented through Step 2
