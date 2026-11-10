"""
Step 3: Generate Candidate List (SimHash-based).

For each unmatched old line, rank unmatched new lines by a combined SimHash
similarity of content and context, then keep the top k=15 candidates.

    content_sim  = 1 - Hamming(content_fp_old, content_fp_new) / bits
    context_sim  = average of above/below SimHash similarities
    ranking_score = 0.6 * content_sim + 0.4 * context_sim

Upper and lower context are fingerprinted and compared separately so they
remain distinct. Levenshtein / textual similarity is NOT used here (Step 4).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .preprocessing import preprocess
from .context_extractor import extract_context, region_text, is_empty_region
from .simhash_util import SIMHASH_BITS, simhash, hamming_distance

CONTENT_WEIGHT = 0.6
CONTEXT_WEIGHT = 0.4
CANDIDATE_K = 15


@dataclass(frozen=True)
class Candidate:
    """One ranked old→new proposal from Step 3."""
    old_line: int
    new_line: int
    score: float                 # combined SimHash similarity in [0, 1]
    content_distance: int        # Hamming distance of content fingerprints
    context_distance: int        # combined Hamming distance of context regions


@dataclass
class CandidateListResult:
    """Structured candidate list: old line → ranked candidates (best first)."""
    by_old_line: dict[int, list[Candidate]] = field(default_factory=dict)

    def for_line(self, old_line: int) -> list[Candidate]:
        return self.by_old_line.get(old_line, [])

    def all_candidates(self) -> list[Candidate]:
        out: list[Candidate] = []
        for old_no in sorted(self.by_old_line):
            out.extend(self.by_old_line[old_no])
        return out

    def format(self) -> str:
        """Human-readable listing of ranked candidates."""
        lines: list[str] = []
        for old_no in sorted(self.by_old_line):
            cands = self.by_old_line[old_no]
            if not cands:
                lines.append(f"  old {old_no}: (no candidates)")
                continue
            ranked = ", ".join(
                f"{c.new_line}({c.score:.3f})" for c in cands
            )
            lines.append(f"  old {old_no}: {ranked}")
        return "\n".join(lines)


@dataclass(frozen=True)
class _ContextFingerprints:
    """Separate SimHash fingerprints for upper and lower context."""
    above_fp: int
    below_fp: int
    above_empty: bool
    below_empty: bool


def _fingerprint_context(context: dict) -> _ContextFingerprints:
    """Build distinct above/below fingerprints for one line's context."""
    above = context.get("above") or []
    below = context.get("below") or []
    above_empty = is_empty_region(above)
    below_empty = is_empty_region(below)
    return _ContextFingerprints(
        above_fp=0 if above_empty else simhash(region_text(above)),
        below_fp=0 if below_empty else simhash(region_text(below)),
        above_empty=above_empty,
        below_empty=below_empty,
    )


def _region_similarity(
    fp_old: int,
    fp_new: int,
    old_empty: bool,
    new_empty: bool,
) -> tuple[float, int] | None:
    """Similarity for one context region, or None if both sides are empty."""
    if old_empty and new_empty:
        return None  # no information from this region
    if old_empty or new_empty:
        return 0.0, SIMHASH_BITS

    dist = hamming_distance(fp_old, fp_new)
    return 1.0 - (dist / SIMHASH_BITS), dist


def _context_similarity(
    old_ctx: _ContextFingerprints,
    new_ctx: _ContextFingerprints,
) -> tuple[float, int]:
    """Average above/below SimHash similarities; empty regions do not inflate."""
    parts: list[tuple[float, int]] = []

    above = _region_similarity(
        old_ctx.above_fp, new_ctx.above_fp,
        old_ctx.above_empty, new_ctx.above_empty,
    )
    if above is not None:
        parts.append(above)

    below = _region_similarity(
        old_ctx.below_fp, new_ctx.below_fp,
        old_ctx.below_empty, new_ctx.below_empty,
    )
    if below is not None:
        parts.append(below)

    if not parts:
        return 0.0, SIMHASH_BITS

    sim = sum(s for s, _ in parts) / len(parts)
    dist = int(round(sum(d for _, d in parts) / len(parts)))
    return sim, dist


def _combined_simhash_score(
    content_fp_old: int,
    content_fp_new: int,
    old_ctx: _ContextFingerprints,
    new_ctx: _ContextFingerprints,
) -> tuple[float, int, int]:
    """Return (ranking_score, content_hamming, context_hamming)."""
    content_dist = hamming_distance(content_fp_old, content_fp_new)
    content_sim = 1.0 - (content_dist / SIMHASH_BITS)
    context_sim, context_dist = _context_similarity(old_ctx, new_ctx)
    score = CONTENT_WEIGHT * content_sim + CONTEXT_WEIGHT * context_sim
    return score, content_dist, context_dist


def generate_candidates(
    old_raw: list[str],
    new_raw: list[str],
    left_list: list[int],
    right_list: list[int],
    k: int = CANDIDATE_K,
) -> CandidateListResult:
    """Build the Step 3 candidate set for every unmatched old line.

    Line numbers in left_list / right_list / Candidate are 1-based.
    If fewer than k right lines exist, all of them are returned.
    """
    result = CandidateListResult()
    if not left_list or not right_list:
        for old_no in left_list:
            result.by_old_line[old_no] = []
        return result

    old_norm = preprocess(old_raw)
    new_norm = preprocess(new_raw)

    # Precompute fingerprints for all unmatched new lines once.
    right_fps: list[tuple[int, int, _ContextFingerprints]] = []
    for new_no in right_list:
        ni = new_no - 1
        content_fp = simhash(new_norm[ni] if 0 <= ni < len(new_norm) else "")
        ctx_fp = _fingerprint_context(extract_context(new_norm, ni))
        right_fps.append((new_no, content_fp, ctx_fp))

    for old_no in left_list:
        oi = old_no - 1
        old_content = old_norm[oi] if 0 <= oi < len(old_norm) else ""
        content_fp_old = simhash(old_content)
        old_ctx = _fingerprint_context(extract_context(old_norm, oi))

        scored: list[Candidate] = []
        for new_no, content_fp_new, new_ctx in right_fps:
            score, content_dist, context_dist = _combined_simhash_score(
                content_fp_old, content_fp_new, old_ctx, new_ctx,
            )
            scored.append(Candidate(
                old_line=old_no,
                new_line=new_no,
                score=score,
                content_distance=content_dist,
                context_distance=context_dist,
            ))

        scored.sort(key=lambda c: (-c.score, c.new_line))
        result.by_old_line[old_no] = scored[:k]

    return result
