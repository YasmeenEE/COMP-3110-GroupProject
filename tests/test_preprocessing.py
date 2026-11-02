"""Unit tests for Step 1 -- preprocessing."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lhdiff import normalize, preprocess


class TestNormalize(unittest.TestCase):

    def test_lowercases(self):
        self.assertEqual(normalize("Public Void FOO"), "public void foo")

    def test_collapses_internal_whitespace(self):
        self.assertEqual(normalize("int    tot   =  0;"), "int tot = 0;")

    def test_strips_ends(self):
        self.assertEqual(normalize("   return tot;   "), "return tot;")

    def test_tabs_become_single_space(self):
        self.assertEqual(normalize("a\t\tb"), "a b")

    def test_blank_line_stays_blank(self):
        self.assertEqual(normalize("    "), "")

    def test_slide_example(self):
        # "After Preprocessing" column from the slides
        self.assertEqual(
            normalize("    FileReader fr = new FileReader(path);"),
            "filereader fr = new filereader(path);")


class TestPreprocess(unittest.TestCase):

    def test_applies_to_every_line(self):
        src = ["public void  Foo(){", "    int  X = 0;", "}"]
        self.assertEqual(
            preprocess(src),
            ["public void foo(){", "int x = 0;", "}"])


if __name__ == "__main__":
    unittest.main()
