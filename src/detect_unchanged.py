"""
Step 2: Finding Unchanged Lines.

The normalised files (from Step 1) are compared with the Unix diff algorithm.
Lines that diff considers equal are mapped directly (old line -> new line).
Everything inside a replace / delete / insert block cannot be matched by diff
alone and is collected into two lists, exactly as the slides describe:

    left list   old line numbers still to be resolved (deleted or changed)
    right list  new line numbers still to be resolved (added or changed)

These lists are the input to Step 3 (candidate generation), which is outside
the scope of this project.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

from .preprocessing import preprocess


@dataclass
class Step2Result:
    """Outcome of Steps 1 + 2."""
    # old line number -> new line number, for lines diff considers unchanged
    mapping: dict[int, int] = field(default_factory=dict)
    # old line numbers left to resolve (deleted or changed)
    left_list: list[int] = field(default_factory=list)
    # new line numbers left to resolve (added or changed)
    right_list: list[int] = field(default_factory=list)

    def format_mapping(self) -> str:
        """Human-readable 'old-new' lines, sorted by old line number."""
        return "\n".join(f"{o}-{n}" for o, n in sorted(self.mapping.items()))


def detect_unchanged(old_raw: list[str], new_raw: list[str]) -> Step2Result:
    """Run Steps 1 + 2 on two files given as lists of raw lines.

    Line numbers in the result are 1-based.
    """
    old_norm = preprocess(old_raw)   # Step 1
    new_norm = preprocess(new_raw)   # Step 1

    result = Step2Result()
    matcher = difflib.SequenceMatcher(a=old_norm, b=new_norm, autojunk=False)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            # unchanged run: map each old line to the aligned new line
            for off in range(i2 - i1):
                result.mapping[i1 + off + 1] = j1 + off + 1
        else:
            # 'replace', 'delete', 'insert' -> lines to resolve later
            result.left_list.extend(range(i1 + 1, i2 + 1))
            result.right_list.extend(range(j1 + 1, j2 + 1))

    return result
