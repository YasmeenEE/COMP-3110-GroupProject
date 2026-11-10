# LHDiff - Steps 1–4

This is our COMP 3110 project. We are using Python to compare two versions of a file and find which lines in the old file match lines in the new file.

We have implemented the first four steps of LHDiff.

## Step 1: Preprocessing

Prepare each line before comparing:

- Lowercase all letters
- Collapse extra whitespace to a single space
- Trim leading/trailing spaces

Example:

Before: `FileReader fr = new FileReader(path);`

After: `filereader fr = new filereader(path);`

Code: `src/preprocessing.py`

## Step 2: Detect Unchanged Lines

Compare normalized files with Python's `difflib.SequenceMatcher`.

Results:

- **Mapping:** exact unchanged matches (`old-new`)
- **Left list:** old lines still unresolved
- **Right list:** new lines still unresolved

Code: `src/detect_unchanged.py`

## Step 3: Generate Candidate List (SimHash)

For each unmatched old line, rank possible new-line matches without using Levenshtein:

1. Build a 32-bit SimHash fingerprint of the line **content**
2. Build separate SimHash fingerprints for **upper** and **lower** context (up to 4 lines each)
3. Compare old/new fingerprints with Hamming distance (XOR + bit count)
4. Convert distances to similarity and combine with the 60/40 weights:

```text
content_sim = 1 - Hamming(content) / 32
context_sim = average of above↔above and below↔below similarities
score       = 0.6 * content_sim + 0.4 * context_sim
```

5. Keep the top **k=15** candidates per old line (or all if fewer than 15)

Empty / punctuation-only context regions are ignored so they do not inflate scores. Upper and lower context stay distinct.

Code:

- `src/simhash_util.py` — SimHash + Hamming distance
- `src/context_extractor.py` — above/below context windows
- `src/generate_candidates.py` — candidate ranking

## Step 4: Resolve Conflicts

For each old line, score only its Step 3 candidates with **textual** similarity (not SimHash):

```text
combined = 0.6 * content_similarity + 0.4 * context_similarity
```

- Content similarity: RapidFuzz ratio
- Context similarity: TF-IDF cosine on above/below regions separately

Keep the best one-to-one matches that clear the threshold (default `0.45`).

Code:

- `src/similarity.py` — content similarity
- `src/context_similarity.py` — context similarity
- `src/match_candidates.py` — conflict resolution

## Project Files

- `src/preprocessing.py` — Step 1
- `src/detect_unchanged.py` — Step 2
- `src/simhash_util.py` — SimHash helpers
- `src/context_extractor.py` — context windows
- `src/generate_candidates.py` — Step 3
- `src/similarity.py` — content similarity (Step 4)
- `src/context_similarity.py` — context similarity (Step 4)
- `src/match_candidates.py` — Step 4
- `src/__init__.py` — package exports
- `main.py` — CLI entry point
- `examples/` — sample old/new files
- `requirements.txt` — dependencies
- `README.md` — this file

## Setup

Requires Python 3.9+.

```bash
cd COMP-3110-GroupProject
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Dependencies: `rapidfuzz`, `scikit-learn`

## How to Run

```bash
python main.py examples/filereader_old.txt examples/filereader_new.txt
```

Example output:

```text
# Step 2: unchanged lines (old-new):
1-1
2-3
4-5
7-9

# Left list (old lines to resolve):
  3, 5, 6, 8
# Right list (new lines to resolve):
  2, 4, 6, 7, 8

# Step 3: SimHash candidate list (new_line(score), best first):
  old 3: 4(0.731), 6(0.556), 2(0.512), 7(0.431), 8(0.400)
  old 5: 6(0.812), 4(0.688), 7(0.600), 2(0.556), 8(0.475)
  old 6: 7(0.738), 6(0.500), 8(0.463), 2(0.425), 4(0.406)
  old 8: 8(0.788), 6(0.537), 2(0.438), 7(0.400), 4(0.344)

# Step 4: similarity matches (old-new):
3-4
5-6
6-7

# Final mapping (old-new):
1-1
2-3
3-4
4-5
5-6
6-7
7-9

# Still unmatched (old / deleted):
  8
# Still unmatched (new / added):
  2, 8
```

`2-3` means old line 2 matches new line 3. In Step 3, `old 3: 4(0.731)` means new line 4 is the best SimHash candidate for old line 3 with score 0.731.

Show normalized lines (Step 1):

```bash
python main.py examples/filereader_old.txt examples/filereader_new.txt --show-normalized
```

### Steps 1–3 only

```python
from src import detect_unchanged, generate_candidates

old = open("examples/filereader_old.txt").read().splitlines()
new = open("examples/filereader_new.txt").read().splitlines()

res = detect_unchanged(old, new)
cands = generate_candidates(old, new, res.left_list, res.right_list)

print(res.format_mapping())
print(cands.format())
```

## Using the Code

```python
from src import (
    preprocess,
    detect_unchanged,
    generate_candidates,
    match_changed_lines,
)

old_lines = [...]
new_lines = [...]

res = detect_unchanged(old_lines, new_lines)
candidates = generate_candidates(
    old_lines, new_lines, res.left_list, res.right_list
)
matches = match_changed_lines(
    old_lines, new_lines, res.left_list, res.right_list, candidates=candidates
)
```

## Next Steps

Still to do:

- **Step 5:** Detect line splits (one old line → several consecutive new lines)
