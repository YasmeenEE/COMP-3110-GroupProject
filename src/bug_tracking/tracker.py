"""SZZ-style candidate discovery with LHDiff history tracing and evidence."""
from __future__ import annotations

import ast
from difflib import SequenceMatcher
from functools import lru_cache

from ..line_mapping import map_lines
from .classifier import classify_fix, is_source_path
from .git_repository import GitError, GitRepository


def affected_old_lines(old: tuple[str, ...], new: tuple[str, ...]) -> list[int]:
    """Use raw, case-sensitive text: preprocessing would hide real fixes."""
    return [n for tag, a, b, _, _ in SequenceMatcher(
        a=old, b=new, autojunk=False
    ).get_opcodes() if tag in {'replace', 'delete'} for n in range(a + 1, b + 1)]


def is_code_line(line: str, path: str = '') -> bool:
    """Conservative whole-line comment/blank filter; no language parser."""
    text = line.strip()
    if not text or text.startswith(('//', '/*', '*/', '* ', '<!--')):
        return False
    # C/C++ preprocessor directives and decrement expressions are code.
    hash_languages = ('.py', '.rb', '.sh', '.bash', '.pl', '.r', '.yaml', '.yml', '.toml', '.ps1')
    if text.startswith('#') and (path.lower().endswith(hash_languages) or path.endswith('Makefile')):
        return False
    return not (text.startswith('-- ') and path.lower().endswith('.sql'))


def code_line_numbers(path: str, lines: tuple[str, ...]) -> set[int]:
    """Filter obvious comments; also exclude actual Python docstring nodes."""
    eligible = {n for n, text in enumerate(lines, 1) if is_code_line(text, path)}
    if path.endswith('.py'):
        try:
            tree = ast.parse('\n'.join(lines))
        except (SyntaxError, ValueError):
            return eligible
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if ast.get_docstring(node, clean=False) is not None:
                    doc = node.body[0]
                    eligible.difference_update(range(doc.lineno, doc.end_lineno + 1))
    return eligible


def same_text(old: str, new_parts: list[str], ignore_indentation: bool = False) -> bool:
    """Preserve raw text by default; splits join trimmed fragments with spaces."""
    if len(new_parts) == 1 and not ignore_indentation:
        return old == new_parts[0]
    return old.strip() == ' '.join(part.strip() for part in new_parts)


class BugTracker:
    def __init__(self, repository: GitRepository, max_depth: int = 500,
                 ignore_indentation: bool = False):
        if max_depth < 1:
            raise ValueError('max_depth must be positive')
        self.repo = repository
        self.max_depth = max_depth
        self.ignore_indentation = ignore_indentation

    @lru_cache(maxsize=128)
    def mapping(self, parent: str, sha: str, old_path: str, new_path: str) -> dict[int, list[int]]:
        return map_lines(list(self.repo.lines(parent, old_path)), list(self.repo.lines(sha, new_path)))

    def trace(self, sha: str, path: str, line: int) -> dict:
        """Walk to the latest substantive edit; stop at ambiguous boundaries."""
        steps = []
        for _ in range(self.max_depth):
            commit = self.repo.commit(sha)
            if not commit.parents:
                if self.repo.shallow:
                    return {'status': 'unresolved', 'reason': 'shallow history boundary', 'trace': steps}
                return self._origin(sha, path, line, 'root commit', steps)
            if len(commit.parents) != 1:
                return {'status': 'unresolved', 'reason': 'merge history boundary', 'trace': steps}
            parent = commit.parents[0]
            change = next((c for c in self.repo.changes(parent, sha) if c.new_path == path), None)
            if change is None:
                sha = parent
                continue
            if change.old_path is None:
                return self._origin(sha, path, line, 'file added', steps)
            old_path = change.old_path
            old, new = self.repo.lines(parent, old_path), self.repo.lines(sha, path)
            mapping = self.mapping(parent, sha, old_path, path)
            preceding = [(o, group) for o, group in mapping.items() if line in group]
            if len(preceding) == 1:
                old_line, group = preceding[0]
                if same_text(old[old_line - 1], [new[n - 1] for n in group], self.ignore_indentation):
                    steps.append({'commit': sha, 'path': path, 'line': line,
                                  'parent_path': old_path, 'parent_line': old_line,
                                  'kind': 'split' if len(group) > 1 else 'mapped unchanged text'})
                    sha, path, line = parent, old_path, old_line
                    continue
            return self._origin(sha, path, line, 'line added or substantively changed', steps)
        return {'status': 'unresolved', 'reason': 'history depth limit', 'trace': steps}

    def _origin(self, sha: str, path: str, line: int, reason: str, steps: list[dict]) -> dict:
        commit = self.repo.commit(sha)
        return {'status': 'candidate', 'commit': sha, 'path': path, 'line': line,
                'author': commit.author, 'date': commit.date, 'subject': commit.message.splitlines()[0],
                'reason': reason, 'trace': steps}

    def analyze_fix(self, revision: str, explicit: bool = False) -> dict:
        sha = self.repo.resolve(revision)
        commit = self.repo.commit(sha)
        result = {'fix_commit': sha, 'subject': commit.message.splitlines()[0],
                  'classification': None, 'status': 'skipped', 'evidence': [], 'notes': [],
                  'candidates': []}
        if len(commit.parents) != 1:
            result['notes'].append('Fix must have exactly one parent; root/merge fixes are unsupported.')
            return result
        parent = commit.parents[0]
        changes = self.repo.changes(parent, sha)
        classification = classify_fix(commit.message, [c.new_path or c.old_path for c in changes])
        result['classification'] = classification.to_dict()
        if not explicit and not classification.is_bug_fix:
            return result
        result['status'] = 'analyzed'
        if explicit:
            result['notes'].append('Fix selected explicitly; commit-message classification was overridden.')
        for change in changes:
            path = change.old_path
            if not path or not is_source_path(path):
                continue
            try:
                old = self.repo.lines(parent, path)
                new = self.repo.lines(sha, change.new_path) if change.new_path else ()
                affected = affected_old_lines(old, new)
                # Skip unchanged mapped text; indentation follows the selected policy.
                mapping = self.mapping(parent, sha, path, change.new_path) if change.new_path and affected else {}
                eligible = code_line_numbers(path, old)
                for line in affected:
                    if line not in eligible:
                        continue
                    group = mapping.get(line, [])
                    if group and same_text(old[line - 1], [new[n - 1] for n in group], self.ignore_indentation):
                        continue
                    try:
                        origin = self.trace(parent, path, line)
                    except GitError as exc:
                        origin = {'status': 'unresolved', 'reason': str(exc), 'trace': []}
                    result['evidence'].append({'fix_path': change.new_path, 'parent_path': path,
                                               'parent_line': line, 'old_text': old[line - 1],
                                               'origin': origin})
            except GitError as exc:
                result['notes'].append(f'{path}: {exc}')
        groups = {}
        for evidence in result['evidence']:
            origin = evidence['origin']
            if origin['status'] == 'candidate':
                groups.setdefault(origin['commit'], []).append(evidence)
        result['candidates'] = [
            {'commit': candidate, 'subject': items[0]['origin']['subject'],
             'supporting_lines': len(items)}
            for candidate, items in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))
        ]
        if not result['evidence']:
            result['notes'].append('No traceable old code lines. Addition-only fixes require another technique.')
        return result
