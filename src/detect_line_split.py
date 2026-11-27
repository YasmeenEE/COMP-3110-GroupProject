"""
Step 5: Detect line splits (slides 41-42).

Finds old lines that were split over several consecutive new lines,
e.g. L40 -> {R20, R21, R22} on slide 42.
"""

from __future__ import annotations

from collections import Counter

from .preprocessing import normalize, preprocess
from .resolve_conflicts import calculate_text_similarity

# Not given in the slides. Real splits score 0.9+, false ones 0.7 or less.
SPLIT_THRESHOLD = 0.8


def concatenate_lines(new_norm: list[str], line_numbers: list[int]) -> str:
    """Join new lines with a space and normalize the result."""
    return normalize(" ".join(new_norm[n - 1] for n in line_numbers))


def similarity_upper_bound(a: str, b: str) -> float:
    """Highest similarity a and b could have, without running Levenshtein."""
    max_length = max(len(a), len(b))
    if max_length == 0:
        return 1.0

    # Each character only one side has needs at least one edit.
    a_chars, b_chars = Counter(a), Counter(b)
    only_in_a = sum((a_chars - b_chars).values())
    only_in_b = sum((b_chars - a_chars).values())
    return 1.0 - max(only_in_a, only_in_b) / max_length


def could_cross_threshold(
    old_line: str,
    new_norm: list[str],
    start: int,
    allowed_new: set[int],
    threshold: float,
) -> bool:
    """Check if any group starting at `start` could pass the threshold.

    Only used to skip slow Levenshtein calls. It never changes the result.
    """
    group = [start]
    next_line = start + 1

    while next_line <= len(new_norm) and next_line in allowed_new:
        group.append(next_line)
        joined = concatenate_lines(new_norm, group)

        if similarity_upper_bound(old_line, joined) > threshold:
            return True

        # Joined text is already too long, and it only gets longer.
        if len(old_line) <= threshold * len(joined):
            return False

        next_line += 1

    return False


def grow_split(
    old_line: str,
    new_norm: list[str],
    start: int,
    allowed_new: set[int],
) -> tuple[list[int], float]:
    """Add lines after `start` until the similarity stops going up."""
    group = [start]
    best = calculate_text_similarity(old_line, new_norm[start - 1])
    next_line = start + 1

    while next_line <= len(new_norm) and next_line in allowed_new:
        joined = concatenate_lines(new_norm, group + [next_line])
        similarity = calculate_text_similarity(old_line, joined)

        if similarity <= best:
            break

        group.append(next_line)
        best = similarity
        next_line += 1

    return group, best


def detect_line_splits(
    old_raw: list[str],
    new_raw: list[str],
    unmapped_old: list[int],
    unmapped_new: list[int],
    step4_matches: dict[int, int] | None = None,
    threshold: float = SPLIT_THRESHOLD,
) -> dict[int, list[int]]:
    """
    Step 5: map old lines to groups of consecutive new lines.

    Returns {old line: [new lines]}. Step 4 can match an old line to just
    one piece of a split (slide 41 maps L40 -> R20), so a Step 4 match can
    be grown into a split. The split then replaces the Step 4 match.
    """
    step4_matches = step4_matches or {}
    if not unmapped_new:
        return {}

    old_norm = preprocess(old_raw)
    new_norm = preprocess(new_raw)

    allowed = {old_no: set(unmapped_new) for old_no in unmapped_old}
    for old_no, new_no in step4_matches.items():
        allowed[old_no] = set(unmapped_new) | {new_no}

    proposals = []

    for old_no, allowed_new in allowed.items():
        old_line = old_norm[old_no - 1]
        if not old_line:
            continue

        step4_line = step4_matches.get(old_no)

        for start in sorted(allowed_new):
            # A blank start line adds no text and would end up in the split.
            if not new_norm[start - 1]:
                continue

            if not could_cross_threshold(
                old_line, new_norm, start, allowed_new, threshold
            ):
                continue

            group, similarity = grow_split(
                old_line, new_norm, start, allowed_new
            )

            # A single line is a one-to-one match, which is Step 4's job.
            if len(group) < 2 or similarity <= threshold:
                continue

            # Only replace a Step 4 match with a split that keeps its line
            # and fits the old line better.
            if step4_line is not None:
                if step4_line not in group:
                    continue
                alone = calculate_text_similarity(
                    old_line, new_norm[step4_line - 1]
                )
                if similarity <= alone:
                    continue

            proposals.append((similarity, old_no, group))

    # Same order as Step 4: best score first, then smaller line movement.
    proposals.sort(
        key=lambda item: (
            -item[0],
            abs(item[1] - item[2][0]),
            item[1],
            item[2][0],
        )
    )

    used_old = set()
    used_new = set()
    splits = {}

    for similarity, old_no, group in proposals:
        if old_no in used_old or any(n in used_new for n in group):
            continue

        splits[old_no] = group
        used_old.add(old_no)
        used_new.update(group)

    return dict(sorted(splits.items()))
