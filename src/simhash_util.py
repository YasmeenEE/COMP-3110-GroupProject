"""
SimHash fingerprints and Hamming distance for Step 3 candidate generation.

Fingerprints are fixed-width (32 bits, matching the course slides). Token
hashes are MD5-based so results are deterministic across runs.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter

SIMHASH_BITS = 32
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> list[str]:
    """Split text into word-ish tokens for SimHash."""
    if not text or not text.strip():
        return []
    return _TOKEN_RE.findall(text)


def _token_hash(token: str) -> int:
    """Deterministic unsigned SIMHASH_BITS-wide hash of one token."""
    digest = hashlib.md5(token.encode("utf-8")).digest()
    value = int.from_bytes(digest, "big")
    return value & ((1 << SIMHASH_BITS) - 1)


def simhash(text: str) -> int:
    """Compute a SimHash fingerprint of `text`.

    Empty / whitespace-only text returns fingerprint 0.
    """
    tokens = tokenize(text)
    if not tokens:
        return 0

    weights = Counter(tokens)
    bit_scores = [0] * SIMHASH_BITS
    for token, weight in weights.items():
        h = _token_hash(token)
        for i in range(SIMHASH_BITS):
            if (h >> i) & 1:
                bit_scores[i] += weight
            else:
                bit_scores[i] -= weight

    fingerprint = 0
    for i in range(SIMHASH_BITS):
        if bit_scores[i] > 0:
            fingerprint |= 1 << i
    return fingerprint


def hamming_distance(a: int, b: int) -> int:
    """Number of differing bits between two fingerprints (XOR + popcount)."""
    return (a ^ b).bit_count()


def hamming_similarity(a: int, b: int) -> float:
    """Convert Hamming distance to similarity in [0, 1] (1 == identical)."""
    return 1.0 - (hamming_distance(a, b) / SIMHASH_BITS)
