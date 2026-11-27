"""Command-line entry point for the project's bug-tracking extension."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from src.bug_tracking import BugTracker, GitError, GitRepository


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Trace likely bug-introducing changes using LHDiff and Git history.')
    parser.add_argument('repository', help='path to a local Git repository')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--fix', action='append', help='explicit fix SHA/ref; repeat for multiple fixes')
    mode.add_argument('--ref', default='HEAD', help='branch/ref to scan (default HEAD)')
    parser.add_argument('--limit', type=int, default=100, help='maximum commits to scan (default 100)')
    parser.add_argument('--max-depth', type=int, default=500, help='maximum ancestor steps per affected line')
    parser.add_argument('--ignore-indentation', action='store_true',
                        help='skip outer whitespace edits; use only when indentation is not semantic')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    parser.add_argument('--output', type=Path, help='save the report to this file')
    args = parser.parse_args(argv)
    if args.limit < 1 or args.max_depth < 1:
        parser.error('--limit and --max-depth must be positive')
    try:
        repo = GitRepository(args.repository)
        tracker = BugTracker(repo, args.max_depth, args.ignore_indentation)
        revisions = args.fix or repo.revisions(args.ref, args.limit)
        analyzed = [tracker.analyze_fix(revision, explicit=bool(args.fix)) for revision in revisions]
        report = {'schema_version': 1, 'method': 'LHDiff-assisted SZZ heuristic',
                  'warning': 'Candidates are evidence for review, not proof of bug causation.',
                  'ignore_indentation': args.ignore_indentation,
                  'shallow_history': repo.shallow, 'commits_examined': len(revisions),
                  'skipped_commits': sum(r['status'] == 'skipped' for r in analyzed),
                  'fixes': [r for r in analyzed if r['status'] != 'skipped' or args.fix]}
        if args.format == 'json':
            output = json.dumps(report, indent=2, ensure_ascii=False)
        else:
            lines = [report['method'], report['warning'],
                     f"Examined {len(revisions)} commits; {len(report['fixes'])} selected fixes."]
            if repo.shallow:
                lines.append('WARNING: shallow history; boundary results remain unresolved.')
            for fix in report['fixes']:
                lines.append(f"\nFix {fix['fix_commit'][:12]}: {fix['subject']}")
                for candidate in fix['candidates']:
                    lines.append(f"  Candidate {candidate['commit'][:12]} ({candidate['supporting_lines']} lines): {candidate['subject']}")
                for evidence in fix['evidence']:
                    origin = evidence['origin']
                    target = origin.get('commit', 'unresolved')[:12]
                    lines.append(f"    {evidence['parent_path']}:{evidence['parent_line']} -> {target}: {origin['reason']}")
                lines.extend(f'  Note: {note}' for note in fix['notes'])
            output = '\n'.join(lines)
        if args.output:
            args.output.write_text(output + '\n', encoding='utf-8')
        else:
            print(output)
        return 0
    except (GitError, OSError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
