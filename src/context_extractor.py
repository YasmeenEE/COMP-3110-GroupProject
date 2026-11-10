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
        "below": below
    }