"""Read-only Git access, with bounded caches and no working-tree checkout."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os
import subprocess


class GitError(ValueError):
    """A repository or revision could not be read safely."""


@dataclass(frozen=True)
class Commit:
    sha: str
    parents: tuple[str, ...]
    author: str
    date: str
    message: str


@dataclass(frozen=True)
class Change:
    status: str
    old_path: str | None
    new_path: str | None


class GitRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        self.run('rev-parse', '--git-dir')
        self.shallow = self.run('rev-parse', '--is-shallow-repository').strip() == 'true'

    def run(self, *args: str) -> str:
        """Use argument arrays, disable external diff/text converters and pagers."""
        env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GIT_PAGER': 'cat',
               'GIT_OPTIONAL_LOCKS': '0', 'GIT_NO_REPLACE_OBJECTS': '1',
               'GIT_CEILING_DIRECTORIES': str(self.path.parent)}
        try:
            result = subprocess.run(
                ['git', '-c', 'core.quotePath=false', '-C', str(self.path), *args],
                capture_output=True, env=env, timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GitError(f'Cannot run Git: {exc}') from exc
        if result.returncode:
            raise GitError(result.stderr.decode('utf-8', errors='replace').strip())
        try:
            return result.stdout.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise GitError('Non-UTF-8 file: convert its encoding before analysis') from exc

    def resolve(self, revision: str) -> str:
        return self.run('rev-parse', '--verify', '--end-of-options', revision + '^{commit}').strip()

    @lru_cache(maxsize=4096)
    def commit(self, sha: str) -> Commit:
        parts = self.run('show', '-s', '--format=%H%x00%P%x00%an%x00%aI%x00%B', sha).split('\0', 4)
        return Commit(parts[0], tuple(parts[1].split()), parts[2], parts[3], parts[4].strip())

    @lru_cache(maxsize=256)
    def lines(self, sha: str, path: str) -> tuple[str, ...]:
        text = self.run('show', f'{sha}:{path}')
        if '\0' in text:
            raise GitError(f'Binary file: {path}')
        return tuple(text.splitlines())

    @lru_cache(maxsize=512)
    def changes(self, parent: str, sha: str) -> tuple[Change, ...]:
        fields = self.run('diff', '--no-ext-diff', '--no-textconv', '--name-status',
                          '-z', '-M', parent, sha, '--').split('\0')
        changes = []
        i = 0
        while i < len(fields) and fields[i]:
            status, path = fields[i], fields[i + 1]
            i += 2
            if status.startswith(('R', 'C')):
                changes.append(Change(status, path, fields[i]))
                i += 1
            else:
                changes.append(Change(status, None if status == 'A' else path,
                                      None if status == 'D' else path))
        return tuple(changes)

    def revisions(self, ref: str, limit: int) -> list[str]:
        return self.run('rev-list', f'--max-count={limit}', self.resolve(ref)).splitlines()
