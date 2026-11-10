"""
Step 4: Resolve conflicts using textual similarity on Step 3 candidates.

For each old line, score only its SimHash candidate set with the existing
content + context textual similarity, then greedily pick the best one-to-one
matches that clear the threshold.

    combined = 0.6 * content_similarity + 0.4 * context_similarity
"""

from __future__ import annotations

from .preprocessing import preprocess
from .similarity import calculate_content_similarity
from .context_extractor import extract_context
from .context_similarity import calculate_context_similarity
from .generate_candidates import CandidateListResult

CONTENT_WEIGHT = 0.6
CONTEXT_WEIGHT = 0.4
THRESHOLD = 0.45


def combined_similarity(
    old_line: str,
    new_line: str,
    old_context: dict,
    new_context: dict,
) -> float:
    """Weighted content + context textual score in [0, 1]."""
    content = calculate_content_similarity(old_line, new_line)
    context = calculate_context_similarity(old_context, new_context)
    return CONTENT_WEIGHT * content + CONTEXT_WEIGHT * context


def match_changed_lines(
    old_raw: list[str],
    new_raw: list[str],
    left_list: list[int],
    right_list: list[int],
    candidates: CandidateListResult | None = None,
    threshold: float = THRESHOLD,
) -> dict[int, int]:
    """Map unresolved old lines to new lines via textual similarity.

    If `candidates` (Step 3) is provided, only those pairs are scored.
    Otherwise falls back to scoring every left×right pair.

    Line numbers are 1-based (same convention as Step 2 / Step 3).
    """
    if not left_list or not right_list:
        return {}

    old_norm = preprocess(old_raw)
    new_norm = preprocess(new_raw)

    proposals: list[tuple[float, int, int]] = []

    if candidates is not None:
        pair_iter = (
            (c.old_line, c.new_line)
            for c in candidates.all_candidates()
        )
    else:
        pair_iter = (
            (old_no, new_no)
            for old_no in left_list
            for new_no in right_list
        )

    seen: set[tuple[int, int]] = set()
    for old_no, new_no in pair_iter:
        key = (old_no, new_no)
        if key in seen:
            continue
        seen.add(key)

        oi, ni = old_no - 1, new_no - 1
        score = combined_similarity(
            old_norm[oi],
            new_norm[ni],
            extract_context(old_norm, oi),
            extract_context(new_norm, ni),
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
