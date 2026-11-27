"""
Run Steps 1–5 of LHDiff on two files.

How to run: python main.py OLD_FILE NEW_FILE [--show-normalized]

  Step 1–2: preprocess and find exact unchanged lines
  Step 3:   SimHash candidate list (top k=15 per old line)
  Step 4:   resolve conflicts with textual similarity on those candidates
  Step 5:   detect line splits (one old line -> several new lines)
"""

from __future__ import annotations

from src import (
    preprocess,
    detect_unchanged,
    generate_candidates,
    resolve_conflicts,
    detect_line_splits,
)


def _read(path: str) -> list[str]:
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def _format_pairs(mapping: dict[int, int]) -> str:
    return "\n".join(f"{o}-{n}" for o, n in sorted(mapping.items()))


def _format_splits(splits: dict[int, list[int]], replaced: dict[int, int]) -> str:
    """Slide 42 notation, e.g. L40 -> {R20, R21, R22}."""
    lines = []
    for o, group in sorted(splits.items()):
        text = f"L{o} -> {{{', '.join(f'R{n}' for n in group)}}}"
        if o in replaced:
            text += f"   (replaces Step 4 match {o}-{replaced[o]})"
        lines.append(text)
    return "\n".join(lines)


def _format_final(mapping: dict[int, int], splits: dict[int, list[int]]) -> str:
    """One old-new pair per line. A split gives a pair for each new line."""
    pairs = list(mapping.items())
    pairs += [(o, n) for o, group in splits.items() for n in group]
    return "\n".join(f"{o}-{n}" for o, n in sorted(pairs))


def _main(argv: list[str]) -> int:
    import argparse

    p = argparse.ArgumentParser(
        description="LHDiff Steps 1–5: unchanged lines, SimHash candidates, "
                    "conflict resolution, then line splits.")
    p.add_argument("old_file")
    p.add_argument("new_file")
    p.add_argument("--show-normalized", action="store_true",
                   help="also print the normalised (Step 1) version of each file")
    args = p.parse_args(argv)

    old_raw = _read(args.old_file)
    new_raw = _read(args.new_file)

    if args.show_normalized:
        print("# Step 1: normalised OLD file:")
        for i, l in enumerate(preprocess(old_raw), 1):
            print(f"  {i:>3}: {l}")
        print("# Step 1: normalised NEW file:")
        for i, l in enumerate(preprocess(new_raw), 1):
            print(f"  {i:>3}: {l}")
        print()

    res = detect_unchanged(old_raw, new_raw)

    print("# Step 2: unchanged lines (old-new):")
    print(res.format_mapping() or "  (none)")
    print("\n# Left list (old lines to resolve):")
    print("  " + (", ".join(map(str, res.left_list)) or "(empty)"))
    print("# Right list (new lines to resolve):")
    print("  " + (", ".join(map(str, res.right_list)) or "(empty)"))

    candidates = generate_candidates(
        old_raw, new_raw, res.left_list, res.right_list
    )
    print("\n# Step 3: SimHash candidate list (new_line(score), best first):")
    print(candidates.format() or "  (none)")

    similarity_matches = resolve_conflicts(
        old_raw,
        new_raw,
        candidates=candidates,
    )
    res.mapping.update(similarity_matches)

    still_left = [n for n in res.left_list if n not in similarity_matches]
    matched_right = set(similarity_matches.values())
    still_right = [n for n in res.right_list if n not in matched_right]

    print("\n# Step 4: similarity matches (old-new):")
    print(_format_pairs(similarity_matches) or "  (none)")

    splits = detect_line_splits(
        old_raw,
        new_raw,
        still_left,
        still_right,
        step4_matches=similarity_matches,
    )

    # A split replaces the old line's Step 4 match.
    replaced = {o: res.mapping.pop(o) for o in splits if o in similarity_matches}

    split_right = {n for group in splits.values() for n in group}
    still_left = [n for n in still_left if n not in splits]
    still_right = [n for n in still_right if n not in split_right]

    print("\n# Step 5: line splits (old line -> new lines):")
    print(_format_splits(splits, replaced) or "  (none)")

    print("\n# Final mapping (old-new):")
    print(_format_final(res.mapping, splits) or "  (none)")
    print("\n# Still unmatched (old / deleted):")
    print("  " + (", ".join(map(str, still_left)) or "(empty)"))
    print("# Still unmatched (new / added):")
    print("  " + (", ".join(map(str, still_right)) or "(empty)"))
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
