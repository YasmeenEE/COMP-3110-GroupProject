"""Reusable Steps 1–5 pipeline; all line numbers are one-based."""
from __future__ import annotations

from .detect_unchanged import detect_unchanged
from .generate_candidates import generate_candidates
from .resolve_conflicts import resolve_conflicts
from .detect_line_split import detect_line_splits


def map_lines(old: list[str], new: list[str]) -> dict[int, list[int]]:
    """Return one-to-one and one-to-many mappings from the group's mapper."""
    result = detect_unchanged(old, new)
    candidates = generate_candidates(old, new, result.left_list, result.right_list)
    changed = resolve_conflicts(old, new, candidates)
    left = [n for n in result.left_list if n not in changed]
    used_right = set(changed.values())
    right = [n for n in result.right_list if n not in used_right]
    splits = detect_line_splits(old, new, left, right, step4_matches=changed)
    mapping = {o: [n] for o, n in (result.mapping | changed).items()}
    mapping.update(splits)
    return dict(sorted(mapping.items()))
