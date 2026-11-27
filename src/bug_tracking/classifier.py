"""Explainable commit-message heuristics, rather than a trained classifier."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
import re

_FIX = re.compile(r'\b(?:fix(?:e[ds])?|fixing|bugfix|hotfix|resolve[ds]?|resolving|correct(?:s|ed|ing)?)\b', re.I)
_DEFECT = re.compile(r'\b(?:bugs?|errors?|crash(?:es)?|regressions?|defects?|deadlocks?|exceptions?|overflow|underflow|leaks?)\b', re.I)
_NON_CODE = re.compile(r'\b(?:typos?|docs?|documentation|readme|spelling|formatting|whitespace|comments?)\b', re.I)
_ISSUE = re.compile(r'(?:#(\d+)|\b([A-Z][A-Z0-9]+-\d+)\b)')


@dataclass(frozen=True)
class FixClassification:
    is_bug_fix: bool
    strength: str
    reasons: tuple[str, ...]
    issue_ids: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def is_source_path(path: str) -> bool:
    """Exclude documentation/assets; accept arbitrary source languages."""
    p = PurePosixPath(path)
    if any(part.lower() in {'docs', 'doc', 'documentation', '.github'} for part in p.parts[:-1]):
        return False
    if p.name.lower().startswith(('readme', 'license', 'changelog')):
        return False
    return p.suffix.lower() not in {
        '.md', '.rst', '.txt', '.pdf', '.pptx', '.png', '.jpg', '.jpeg', '.gif',
        '.svg', '.ico', '.lock', '.csv', '.ipynb', '.zip', '.mp4',
    }


def classify_fix(message: str, paths: list[str]) -> FixClassification:
    """An issue reference alone does not prove a commit is a bug fix."""
    subject = message.splitlines()[0] if message else ''
    issues = tuple(sorted({a or b for a, b in _ISSUE.findall(message)}))
    if subject.lower().startswith(('revert ', 'merge ')):
        return FixClassification(False, 'none', ('merge or revert subject',), issues)
    if not any(is_source_path(p) for p in paths):
        return FixClassification(False, 'none', ('no source file changes',), issues)
    fix, defect = bool(_FIX.search(subject)), bool(_DEFECT.search(subject))
    if _NON_CODE.search(subject) and not defect:
        return FixClassification(False, 'none', ('documentation or cosmetic subject',), issues)
    if fix and defect:
        return FixClassification(True, 'strong', ('repair verb and defect keyword',), issues)
    if fix:
        return FixClassification(True, 'moderate', ('repair verb in subject',), issues)
    return FixClassification(False, 'none', ('no repair verb in subject',), issues)
