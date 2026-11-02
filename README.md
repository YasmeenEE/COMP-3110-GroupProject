# LHDiff - Steps 1 & 2

This is our COMP 3110 project. We are using Python to compare two versions of a file.

We want to find which lines in the old file match the lines in the new file.

We have worked on the first two steps of LHDiff.

## Step 1: Preprocessing

In this step, we prepare the files before comparing them.

The program:
- Changes capital letters to small letters.
- Removes extra spaces.
- Removes spaces at the start and end of each line.

For example:

Before: `FileReader fr = new FileReader(path);`

After: `filereader fr = new filereader(path);`

The code is in `src/preprocessing.py`.

## Step 2: Detect Unchanged Lines

In this step, we compare the old and new files.

We use Python's `difflib.SequenceMatcher` to find lines that are the same.

The program gives us three results:

- **Mapping:** Lines that match in both files.
- **Left List:** Old lines that still need to be checked.
- **Right List:** New lines that still need to be checked.

The code is in `src/detect_unchanged.py`.

## Project Files

Our project has these files and folders:
- src/preprocessing.py - Code for Step 1.
- src/detect_unchanged.py - Code for Step 2.
- src/__init__.py - Helps us use the Python functions.
- main.py - Runs our program.
- examples/ - Has example files.
- tests/ - Has files to test our code.
- README.md - Explains our project.

## How to Run

Open the project in VS Code.

Run this command in the terminal:

```bash
python main.py examples/filereader_old.txt examples/filereader_new.txt
```

Example output:

```text
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

For example, `2-3` means line 2 in the old file matches line 3 in the new file.

To see the lines after Step 1, use:

```bash
python main.py examples/filereader_old.txt examples/filereader_new.txt --show-normalized
```

## Using the Code

We can also use the functions in another Python file.

```python
from src import preprocess, detect_unchanged

norm = preprocess(["public void  Foo(){", "    int X = 0;"])

res = detect_unchanged(old_lines, new_lines)

res.mapping
res.left_list
res.right_list
```

## Next Steps

We still need to work on:

- **Step 3:** Find possible matching lines.
- **Step 4:** Choose the best matches.
- **Step 5:** Find lines that were split into more than one line.