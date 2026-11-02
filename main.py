"""
Run Steps 1 and 2 of LHDiff on two files.

How to run: python main.py OLD_FILE NEW_FILE [--show-normalized]

This shows which lines stayed the same and lists the old and new lines that
still need to be matched. 
Add --show-normalized to also see each file after Step 1 preprocessing.
"""

from __future__ import annotations

from src import preprocess, detect_unchanged


def _read(path: str) -> list[str]:
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def _main(argv: list[str]) -> int:
    import argparse

    p = argparse.ArgumentParser(
        description="LHDiff Steps 1 & 2: preprocess, then find unchanged lines.")
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
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
