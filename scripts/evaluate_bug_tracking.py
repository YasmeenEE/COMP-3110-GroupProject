"""Reproducible synthetic oracle: 25 histories, compared with basic Git blame.

Run from the repository root:
    python scripts/evaluate_bug_tracking.py --output docs/bug_tracking_evaluation.json
These controlled histories supplement, not replace, the course's file datasets.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.bug_tracking import BugTracker, GitRepository


def evaluate() -> dict:
    rows = []
    for suffix in ('py', 'java', 'c', 'js', 'rs'):
        for change in ('direct', 'move', 'indent', 'split', 'rename'):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                def git(*args):
                    return subprocess.run(['git', '-C', directory, *args], capture_output=True,
                                          text=True, check=True).stdout.strip()
                def commit(text, message, path):
                    (root / path).write_text(text, encoding='utf-8')
                    git('add', '-A')
                    git('commit', '-qm', message)
                    return git('rev-parse', 'HEAD')
                git('init', '-q')
                git('config', 'user.name', 'Synthetic Oracle')
                git('config', 'user.email', 'oracle@example.invalid')
                git('config', 'commit.gpgsign', 'false')
                path = f'calculation.{suffix}'
                text = 'begin();\nresult = calculate(first, second, bad_value);\nfinish();\n'
                expected = commit(text, 'Introduce faulty calculation', path)
                if change == 'move':
                    text = 'begin();\nfinish();\nresult = calculate(first, second, bad_value);\n'
                elif change == 'indent':
                    text = 'begin();\n    result = calculate(first, second, bad_value);\nfinish();\n'
                elif change == 'split':
                    text = 'begin();\nresult = calculate(first,\nsecond, bad_value);\nfinish();\n'
                elif change == 'rename':
                    new_path = f'renamed calculation.{suffix}'
                    git('mv', path, new_path)
                    path = new_path
                if change != 'direct':
                    commit(text, f'Non-semantic {change}', path)
                fix = commit(text.replace('bad_value', 'good_value'), 'Fix calculation error (#123)', path)
                result = BugTracker(GitRepository(root), ignore_indentation=True).analyze_fix(fix)
                found = {c['commit'] for c in result['candidates']}
                line = next(i for i, value in enumerate(text.splitlines(), 1) if 'bad_value' in value)
                baseline = git('blame', '--line-porcelain', '-L', f'{line},{line}', fix + '^', '--', path).split()[0]
                rows.append({'case': f'{suffix}/{change}', 'expected_subject': 'Introduce faulty calculation',
                             'lhdiff_exact_match': found == {expected},
                             'basic_blame_exact_match': baseline == expected,
                             'supporting_lines': len(result['evidence'])})
    return {'dataset': '25 controlled synthetic Git histories; not a real-world accuracy estimate',
            'configuration': 'ignore_indentation=True; generated indentation edits are explicitly non-semantic',
            'metric': 'exact candidate-set match against the known introducing commit',
            'cases': len(rows), 'lhdiff_correct': sum(r['lhdiff_exact_match'] for r in rows),
            'basic_blame_correct': sum(r['basic_blame_exact_match'] for r in rows),
            'baseline': 'git blame --line-porcelain (without -w, -M, or -C)', 'results': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = evaluate()
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(text + '\n', encoding='utf-8')
    print(f"LHDiff: {result['lhdiff_correct']}/{result['cases']}; basic blame: {result['basic_blame_correct']}/{result['cases']}")
