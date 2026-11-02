# LHDiff — Steps 1 & 2

A clean, language-independent implementation of the **first two steps** of
LHDiff (Asaduzzaman et al., ICSM 2013), for COMP-3110.

Given two versions of a text file, this project:

1. **Preprocessing** — normalises every line so comparison is robust to
   re-indentation and case-only edits.
2. **Detect Unchanged Lines** — runs the diff algorithm over the normalised
   lines, maps the lines that are unchanged, and splits the rest into the
   **left list** (old lines still to resolve) and **right list** (new lines
   still to resolve).

Steps 3–5 (candidate generation, conflict resolution, line-split detection)
are intentionally **out of scope** here; the left/right lists are exactly the
hand-off point to Step 3.

Pure Python 3 standard library — no installation, no dependencies.

---

## Layout

```
lhdiff_step1_2/
├── lhdiff/
│   ├── __init__.py            # package API
│   ├── preprocessing.py       # Step 1
│   └── detect_unchanged.py    # Step 2
├── main.py                    # command-line entry point
├── tests/
│   ├── test_preprocessing.py
│   └── test_detect_unchanged.py
├── examples/
│   ├── filereader_old.txt     # the slides' Step-2 example (old)
│   └── filereader_new.txt     # the slides' Step-2 example (new)
└── README.md
```

---

## Usage

```bash
python main.py examples/filereader_old.txt examples/filereader_new.txt
```

Output:

```
# Step 2 -- unchanged lines (old-new):
1-1
2-3
4-5
7-9

# Left list (old lines to resolve):
  3, 5, 6, 8
# Right list (new lines to resolve):
  2, 4, 6, 7, 8
```

Add `--show-normalized` to also print the Step 1 output of each file.

### As a library

```python
from lhdiff import preprocess, detect_unchanged

norm = preprocess(["public void  Foo(){", "    int X = 0;"])
# -> ['public void foo(){', 'int x = 0;']

res = detect_unchanged(old_lines, new_lines)
res.mapping      # {old_line: new_line} for unchanged lines
res.left_list    # old line numbers to resolve in Step 3
res.right_list   # new line numbers to resolve in Step 3
```

---

## How it works

### Step 1 — Preprocessing (`lhdiff/preprocessing.py`)

`normalize()` lowercases the line, collapses every run of whitespace to a
single space, and trims the ends. Matches the slides' "After Preprocessing"
column, e.g. `"    FileReader fr = new FileReader(path);"` →
`"filereader fr = new filereader(path);"`.

### Step 2 — Detect Unchanged Lines (`lhdiff/detect_unchanged.py`)

The two normalised files are compared with Python's `difflib.SequenceMatcher`
(the Unix-diff algorithm). For each `equal` block the old/new lines are mapped
1:1; for each `replace` / `delete` / `insert` block the old lines go to the
left list and the new lines go to the right list. Line numbers are 1-based.

---

## Running the tests

```bash
python -m unittest discover -s tests -v
```

The tests check normalisation, the identity mapping, insertions/deletions, and
reproduce the `fileReader` example from the Step-2 slide.
