"""
Steps 3 & 4: Match changed lines using content + context similarity.

Takes the left_list / right_list from Step 2 and proposes one-to-one
mappings for near-matches:

    combined = 0.6 * content_similarity + 0.4 * context_similarity

Pairs that clear the threshold are resolved greedily (highest score first).
"""

from __future__ import annotations

from .preprocessing import preprocess
from .similarity import calculate_content_similarity
from .context_extractor import extract_context
from .context_similarity import calculate_context_similarity

CONTENT_WEIGHT = 0.6
CONTEXT_WEIGHT = 0.4
THRESHOLD = 0.45


def combined_similarity(
    old_line: str,
    new_line: str,
    old_context: dict,
    new_context: dict,
) -> float:
    """Weighted content + context score in [0, 1]."""
    content = calculate_content_similarity(old_line, new_line)
    context = calculate_context_similarity(old_context, new_context)
    return CONTENT_WEIGHT * content + CONTEXT_WEIGHT * context


def match_changed_lines(
    old_raw: list[str],
    new_raw: list[str],
    left_list: list[int],
    right_list: list[int],
    threshold: float = THRESHOLD,
) -> dict[int, int]:
    """Map unresolved old lines to new lines via similarity.

    Line numbers in left_list / right_list / the returned mapping are 1-based
    (same convention as Step 2).
    """
    if not left_list or not right_list:
        return {}

    old_norm = preprocess(old_raw)
    new_norm = preprocess(new_raw)

    proposals: list[tuple[float, int, int]] = []
    for old_no in left_list:
        oi = old_no - 1
        old_ctx = extract_context(old_norm, oi)

        for new_no in right_list:
            ni = new_no - 1
            new_ctx = extract_context(new_norm, ni)
            score = combined_similarity(
                old_norm[oi], new_norm[ni], old_ctx, new_ctx
            )
            if score >= threshold:
                proposals.append((score, old_no, new_no))

    # Greedy one-to-one: highest score wins; each line used once.
    proposals.sort(reverse=True)
    used_left: set[int] = set()
    used_right: set[int] = set()
    matches: dict[int, int] = {}

    for score, old_no, new_no in proposals:
        if old_no in used_left or new_no in used_right:
            continue
        used_left.add(old_no)
        used_right.add(new_no)
        matches[old_no] = new_no

    return matches
