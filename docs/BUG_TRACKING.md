# Bug-introducing change detection

This extension addresses the outline's bug-tracking goal and slides 54–55:
identify likely bug-fix commits and trace the affected old lines to earlier
changes that could have introduced the bug. It uses the group's complete
Steps 1–5 pipeline rather than treating ordinary Git blame as the final answer.

## Run it

Requires Python 3.10+ and Git. Install the existing dependencies:

```bash
python -m pip install -r requirements.txt
python bug_tracker.py /path/to/repository --ref main
python bug_tracker.py /path/to/repository --fix FIX_SHA
python bug_tracker.py /path/to/repository --fix FIX_SHA --format json --output report.json
```

`--fix` can be repeated. It deliberately overrides message classification, so
you can analyze a verified fix with an uninformative commit message. Branch
scanning examines up to 100 reachable commits by default; use `--limit 1000`
for a larger scan. `--max-depth 500` bounds each line's history traversal.
The repository argument must identify the repository directory, not an
arbitrary directory elsewhere. No checkouts, fetches, or working-tree edits
are performed by the analyzer.

The existing file-comparison command remains available:

```bash
python main.py examples/filereader_old.txt examples/filereader_new.txt
```

## Algorithm

1. Classify commit subjects using repair verbs with word boundaries. A defect
   keyword strengthens the classification; issue references are recorded but
   do not establish a fix by themselves. Exclude documentation-only changes,
   cosmetic subjects, merge subjects, and reverts. The four slide examples
   are covered by tests. Strength labels are rule descriptions, not calibrated
   probabilities.
2. Compare the fix with its parent using raw, case-sensitive text. Select the
   old lines removed or replaced by the fix. Ignore blank and obvious whole-line
   comment lines and recognized Python docstrings. Added lines have no previous line to trace.
3. Apply Steps 1–5 to distinguish a repair from a move or line split with the
   same text. Preserve raw text when deciding whether a mapping represents an
   unchanged line: the mapper's lowercasing must not hide case-sensitive fixes.
4. Trace each selected old line backward. Follow unchanged files directly;
   use Git's rename detection and LHDiff mappings when the file changes.
   A mapping only permits traversal when its original case-sensitive text
   matches, or its split fragments reconstruct the old line. Similarity alone
   does not establish that a change is non-semantic.
5. Stop at the latest addition or substantive edit and report it as a candidate.
   Root additions can be candidates. Merge boundaries, shallow history boundaries,
   read failures, and depth exhaustion remain unresolved.
6. Group results by candidate commit, ordered by supporting-line count with
   deterministic SHA tie-breaking. This count measures evidence, not certainty.

The approach follows the SZZ family of heuristics described in
[SZZ Unleashed](https://arxiv.org/abs/1903.01742). Our extension uses LHDiff to
follow line movement and splitting across file versions. It does not execute
code or prove that a candidate caused the bug.

## Report contents

The versioned JSON report includes the fix SHA and subject, classification
reasons, issue IDs, candidate SHAs, supporting-line counts, original affected
text, original file/line, candidate author/date/file/line, and each traversed
mapping. Explicitly selected fixes retain their original classification and
record the override. Unresolved lines and skipped files carry reasons.
Text output is a compact summary of the same evidence.

Results are deterministic for a fixed repository, options, and dependencies.
Bounded caches reuse commit metadata, changed-file lists, file contents, and
line mappings across affected lines and fixes. Git is invoked with argument
arrays, read timeouts, disabled external diff/text conversion, and no shell
interpolation. The analysis reads committed content, including when the working
tree has uncommitted edits.

## Indentation policy

The default preserves whitespace for one-to-one mappings. In Python, YAML,
Makefiles, or other indentation-sensitive input, a whitespace edit can introduce
a defect. For histories where outer whitespace edits are known to be cosmetic:

```bash
python bug_tracker.py /path/to/repository --fix FIX_SHA --ignore-indentation
```

This option trims leading/trailing whitespace for comparison but preserves case
and internal whitespace. Split tracing joins trimmed fragments with spaces;
that remains a text-based approximation, not a language-level equivalence check.

## Validation and evaluation

```bash
python -m unittest discover -s tests -v
python -m scripts.evaluate_bug_tracking --output docs/bug_tracking_evaluation.json
```

The integration tests construct actual temporary Git repositories, then assert
known fix-to-introducing-commit relationships. They cover classification, issue
references, multiple candidates, reorderings, indentation policies, splits,
renames with spaces, case changes, deletion, addition-only fixes, merge and
shallow boundaries, depth limits, binary/encoding errors, invalid input, JSON
output, and working-tree preservation.

The evaluation constructs **25 synthetic histories**, combining five source
extensions with five transformations: direct edit, move, indentation, split,
and rename. The introducing commit is known by construction. The metric is an
exact match of the returned candidate set against that commit. Indentation is
explicitly generated as non-semantic, so the evaluation enables
`ignore_indentation=True`.

The recorded result is **25/25** for the LHDiff-assisted tracker and **10/25**
for basic `git blame --line-porcelain`, without `-w`, `-M`, or `-C`. This is a
narrow baseline and a regression dataset. It is not a comparison against all
SZZ variants, a real-world accuracy estimate, or a substitute for the course's
separate 25-file line-mapping benchmark. `docs/bug_tracking_evaluation.json`
contains each case's result.

## Limits and interpretation

- Commit subjects can misclassify fixes or miss fixes. Use explicit `--fix`
  input after manual inspection when accurate labels matter.
- A fix may contain unrelated changes; all selected old code lines are traced.
  Supporting lines can therefore implicate unrelated commits.
- Addition-only fixes, missing-code defects, cross-file code moves, line merges,
  and semantic refactorings are not reliably resolved. Renames use Git's default
  similarity threshold; major simultaneous rewrites may appear as delete/add.
- Merge fixes are skipped. Tracing stops at merge commits rather than selecting
  an arbitrary parent. A shallow repository can hide introducing history.
- Generic comment filtering is intentionally limited. Multi-line comments,
  embedded-language strings, and language-specific syntax may still contribute noise.
  Actual Python docstrings are excluded when the old file parses successfully.
  File filtering excludes common documentation/assets; it is not a language detector.
- The existing mapper is heuristic. Ambiguous duplicate lines or imperfect
  split mappings can misattribute history. Trace paths are provided for review.
- Cached full-file comparisons can be costly on very large files. Depth/scan
  limits bound traversal; caches bound retained entries, not individual file size.
- Rankings and author fields describe Git evidence. They do not establish fault
  or developer responsibility.
