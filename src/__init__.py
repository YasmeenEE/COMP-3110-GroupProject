"""
LHDiff tracks lines between versions of a file.
This package handles preprocessing and finding unchanged lines, which are the first two steps of LHDiff:

    Step 1 can be found in the file: (src.preprocessing) 
    Step 2 can be found in the file:(src.detect_unchanged)

Public API imports:
    normalize, preprocess            -- Step 1
    detect_unchanged, Step2Result    -- Step 2, 
    

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
