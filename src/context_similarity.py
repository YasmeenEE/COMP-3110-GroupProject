"""
Step 4 context similarity: TF-IDF cosine, upper and lower kept distinct.

Above is compared only to above, and below only to below. The two region
scores are averaged so upper/lower context cannot be swapped without cost.
"""

from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .context_extractor import region_text
from .simhash_util import tokenize


def _cosine(old_text: str, new_text: str) -> float:
    """TF-IDF cosine similarity of two non-empty region strings."""
    vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b")
    try:
        vectors = vectorizer.fit_transform([old_text, new_text])
    except ValueError:
        # Documents had no usable word tokens (e.g. punctuation-only).
        return 0.0
    score = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
    return float(score)


def _region_similarity(old_lines, new_lines) -> float | None:
    """Similarity for one region, or None if both sides lack tokens."""
    old_text = region_text(old_lines)
    new_text = region_text(new_lines)
    old_empty = not tokenize(old_text)
    new_empty = not tokenize(new_text)

    if old_empty and new_empty:
        return None  # no information from this region
    if old_empty or new_empty:
        return 0.0

    return _cosine(old_text, new_text)


def calculate_context_similarity(old_context, new_context):
    """
    Compare two contexts using TF-IDF and Cosine Similarity.

    old_context and new_context are dictionaries containing 'above' and
    'below' lists. Upper and lower windows are scored separately, then
    averaged. Empty regions do not inflate the score.
    """
    scores = []
    for key in ("above", "below"):
        region_score = _region_similarity(
            old_context.get(key) or [],
            new_context.get(key) or [],
        )
        if region_score is not None:
            scores.append(region_score)

    if not scores:
        return 0.0
    return sum(scores) / len(scores)
