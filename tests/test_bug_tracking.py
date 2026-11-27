"""Integration tests build real Git histories with known introducing commits."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from bug_tracker import main
from src.bug_tracking import BugTracker, GitRepository, classify_fix
from src.bug_tracking.tracker import affected_old_lines, code_line_numbers


class History:
    def __init__(self, directory: str):
        self.path = Path(directory)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Test Author')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')

    def git(self, *args: str) -> str:
        return subprocess.run(['git', '-C', str(self.path), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self, text: str, message: str, path: str = 'app.py') -> str:
        target = self.path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
        self.git('add', '--all')
        self.git('commit', '-qm', message)
        return self.git('rev-parse', 'HEAD')


class ClassifierTests(unittest.TestCase):
    def test_course_slide_examples(self):
        examples = [
            ('Refactor authentication logic', ['auth.py'], False),
            ('Fix login error (#123)', ['auth.py'], True),
            ('Fix typo in user documentation\ncloses #234', ['docs/user.md'], False),
            ('Update README to reflect new installation instructions', ['README.md'], False),
        ]
        for message, paths, expected in examples:
            with self.subTest(message=message):
                self.assertEqual(classify_fix(message, paths).is_bug_fix, expected)

    def test_boundaries_and_issue_ids(self):
        for subject in ('prefix login', 'fixture changes', 'closes #42', 'Revert "Fix crash"', 'Merge fix branch'):
            self.assertFalse(classify_fix(subject, ['x.py']).is_bug_fix)
        result = classify_fix('fix: prevent crash ABC-123 (#42)', ['x.rs'])
        self.assertEqual(result.strength, 'strong')
        self.assertEqual(result.issue_ids, ('42', 'ABC-123'))

    def test_python_docstring_filter_keeps_runtime_strings(self):
        lines = ('"""Module docs"""', 'def f():', '    """Function docs"""',
                 '    message = "runtime value"', '    return message')
        self.assertEqual(code_line_numbers('app.py', lines), {2, 4, 5})

    def test_preprocessor_directives_are_code(self):
        self.assertEqual(code_line_numbers('app.c', ('#define LIMIT 0', '-- counter;', '// comment')), {1, 2})
        self.assertEqual(code_line_numbers('app.py', ('# comment', 'run()')), {2})

    def test_raw_case_sensitive_fix_seeds(self):
        self.assertEqual(affected_old_lines(('return User',), ('return user',)), [1])


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.history = History(self.temp.name)

    def tracker(self, max_depth=500):
        return BugTracker(GitRepository(self.temp.name), max_depth, ignore_indentation=True)

    def candidate(self, fix):
        report = self.tracker().analyze_fix(fix)
        self.assertEqual(report['status'], 'analyzed')
        self.assertTrue(report['candidates'], report)
        return report

    def test_modified_line_and_multiple_candidates(self):
        h = self.history
        first = h.commit('a = 0\nb = 0\n', 'initial values')
        second = h.commit('a = 0\nb = -1\n', 'change b')
        fix = h.commit('a = 1\nb = 1\n', 'Fix incorrect values')
        report = self.candidate(fix)
        self.assertEqual({c['commit'] for c in report['candidates']}, {first, second})
        self.assertEqual(len(report['evidence']), 2)

    def test_history_moves_and_indentation(self):
        h = self.history
        bug = h.commit('start()\nreturn bad_value\nfinish()\n', 'introduce behavior')
        h.commit('start()\nfinish()\n    return bad_value\n', 'reorder and indent')
        fix = h.commit('start()\nfinish()\n    return good_value\n', 'Fix return value')
        report = self.candidate(fix)
        self.assertEqual(report['candidates'][0]['commit'], bug)
        self.assertTrue(report['evidence'][0]['origin']['trace'])

    def test_split_history(self):
        h = self.history
        bug = h.commit('result = calculate(first, second, bad_value)\n', 'introduce calculation')
        h.commit('result = calculate(first,\nsecond, bad_value)\n', 'wrap calculation')
        fix = h.commit('result = calculate(first,\nsecond, good_value)\n', 'Fix calculation bug')
        report = self.candidate(fix)
        self.assertEqual(report['candidates'][0]['commit'], bug)
        self.assertIn('split', [s['kind'] for s in report['evidence'][0]['origin']['trace']])

    def test_rename_and_spaces_in_path(self):
        h = self.history
        bug = h.commit('return bad_value\n', 'add implementation')
        h.git('mv', 'app.py', 'new name.py')
        h.git('commit', '-qm', 'rename implementation')
        fix = h.commit('return good_value\n', 'Fix return bug', 'new name.py')
        report = self.candidate(fix)
        self.assertEqual(report['candidates'][0]['commit'], bug)
        self.assertEqual(report['evidence'][0]['origin']['path'], 'app.py')

    def test_case_change_is_substantive(self):
        h = self.history
        h.commit('return user\n', 'initial')
        bug = h.commit('return User\n', 'change symbol case')
        fix = h.commit('return user\n', 'Fix symbol error')
        self.assertEqual(self.candidate(fix)['candidates'][0]['commit'], bug)

    def test_cosmetic_and_comment_fixes_have_no_candidates(self):
        h = self.history
        h.commit('# old comment\nreturn value\n', 'initial')
        fix = h.commit('# new comment\n    return value\n', 'Fix indentation')
        self.assertEqual(self.tracker().analyze_fix(fix)['evidence'], [])

    def test_default_preserves_semantic_indentation(self):
        h = self.history
        h.commit('if enabled:\n    run()\nfinish()\n', 'initial')
        bug = h.commit('if enabled:\n    run()\n    finish()\n', 'change control flow')
        fix = h.commit('if enabled:\n    run()\nfinish()\n', 'Fix indentation bug')
        report = BugTracker(GitRepository(h.path)).analyze_fix(fix)
        self.assertEqual(report['candidates'][0]['commit'], bug)

    def test_addition_only_fix_is_explicitly_unresolved(self):
        h = self.history
        h.commit('run()\n', 'initial')
        fix = h.commit('validate()\nrun()\n', 'Fix validation bug')
        report = self.tracker().analyze_fix(fix)
        self.assertEqual(report['candidates'], [])
        self.assertIn('Addition-only', report['notes'][0])

    def test_deleted_file(self):
        h = self.history
        bug = h.commit('unsafe_call()\n', 'add unsafe behavior')
        (h.path / 'app.py').unlink()
        h.git('add', '-A')
        h.git('commit', '-qm', 'Fix unsafe behavior')
        self.assertEqual(self.candidate('HEAD')['candidates'][0]['commit'], bug)

    def test_depth_limit(self):
        h = self.history
        h.commit('bad()\n', 'initial')
        h.commit('x = 1\n', 'unrelated', 'other.py')
        fix = h.commit('good()\n', 'Fix crash')
        report = self.tracker(max_depth=1).analyze_fix(fix)
        self.assertEqual(report['candidates'], [])
        self.assertEqual(report['evidence'][0]['origin']['reason'], 'history depth limit')

    def test_merge_boundary(self):
        h = self.history
        h.commit('bad()\n', 'initial')
        branch = h.git('branch', '--show-current')
        h.git('checkout', '-qb', 'side')
        h.commit('side()\n', 'side work', 'side.py')
        h.git('checkout', '-q', branch)
        h.commit('main()\n', 'main work', 'other.py')
        h.git('merge', '--no-ff', '-qm', 'merge side', 'side')
        fix = h.commit('good()\n', 'Fix crash')
        report = self.tracker().analyze_fix(fix)
        self.assertEqual(report['evidence'][0]['origin']['reason'], 'merge history boundary')
        self.assertEqual(self.tracker().analyze_fix(fix + '^')['status'], 'skipped')

    def test_shallow_boundary(self):
        h = self.history
        h.commit('bad()\n', 'initial')
        fix = h.commit('good()\n', 'Fix crash')
        with tempfile.TemporaryDirectory() as clone:
            subprocess.run(['git', 'clone', '-q', '--depth=2', h.path.as_uri(), clone], check=True)
            report = BugTracker(GitRepository(clone)).analyze_fix(fix)
            self.assertEqual(report['evidence'][0]['origin']['reason'], 'shallow history boundary')

    def test_binary_and_invalid_encoding_are_reported(self):
        h = self.history
        h.commit('bad()\n', 'initial')
        (h.path / 'binary.dat').write_bytes(b'\0abc')
        (h.path / 'legacy.c').write_bytes(b'\xff')
        h.git('add', '-A')
        h.git('commit', '-qm', 'add binary and legacy data')
        (h.path / 'binary.dat').write_bytes(b'\0def')
        (h.path / 'legacy.c').write_bytes(b'\xfe')
        h.git('add', '-A')
        h.git('commit', '-qm', 'Fix data bug')
        report = self.tracker().analyze_fix('HEAD')
        self.assertEqual(len(report['notes']), 3)
        self.assertEqual(report['candidates'], [])

    def test_explicit_override_and_json_cli(self):
        h = self.history
        h.commit('bad()\n', 'initial')
        h.commit('good()\n', 'Correct behavior without keyword')
        # Explicit mode accepts a fix even when its subject has no repair verb.
        fix = h.commit('best()\n', 'Change behavior')
        self.assertEqual(self.tracker().analyze_fix(fix)['status'], 'skipped')
        output = io.StringIO()
        before = h.git('status', '--porcelain')
        with contextlib.redirect_stdout(output):
            self.assertEqual(main([str(h.path), '--fix', fix, '--format', 'json']), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report['schema_version'], 1)
        self.assertEqual(len(report['fixes']), 1)
        self.assertEqual(before, h.git('status', '--porcelain'))
        self.assertEqual(h.git('rev-parse', 'HEAD'), fix)

    def test_cli_invalid_revision_and_repository(self):
        self.history.commit('run()\n', 'initial')
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([self.temp.name, '--fix', 'missing-ref']), 2)
            with tempfile.TemporaryDirectory() as empty:
                self.assertEqual(main([empty]), 2)


if __name__ == '__main__':
    unittest.main()
