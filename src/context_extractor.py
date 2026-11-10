"""
Extract and represent surrounding context for a target line.

Context is kept as distinct upper (above) and lower (below) windows so
callers can compare them separately instead of flattening both sides.
"""

from .simhash_util import tokenize


def extract_context(lines, target_index, window=4):
    """
    Extract surrounding lines around a target line.

    Args:
        lines: List containing all lines of a file.
        target_index: Zero-based index of the target line.
        window: Number of lines to extract above and below.

    Returns:
        Dictionary containing the lines above and below.
    """

    start = max(0, target_index - window)
    end = min(len(lines), target_index + window + 1)

    above = lines[start:target_index]
    below = lines[target_index + 1:end]

    return {
        "above": above,
        "below": below,
    }


def region_text(lines) -> str:
    """Join one context region (above or below) into a single string."""
    if not lines:
        return ""
    return " ".join(line for line in lines if line is not None)


def is_empty_region(lines) -> bool:
    """True when a context region has no usable word tokens."""
    return not tokenize(region_text(lines))
