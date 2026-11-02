"""Unit tests for Step 2 -- detect unchanged lines."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lhdiff import detect_unchanged


class TestDetectUnchanged(unittest.TestCase):

    def test_identical_files_map_one_to_one(self):
        lines = ["a", "b", "c"]
        res = detect_unchanged(lines, lines)
        self.assertEqual(res.mapping, {1: 1, 2: 2, 3: 3})
        self.assertEqual(res.left_list, [])
        self.assertEqual(res.right_list, [])

    def test_normalization_anchors_reindented_lines(self):
        # case + whitespace differences should still count as unchanged
        old = ["int X = 0;"]
        new = ["   int   x   =   0;"]
        res = detect_unchanged(old, new)
        self.assertEqual(res.mapping, {1: 1})

    def test_insertion_goes_to_right_list(self):
        old = ["a", "b"]
        new = ["a", "inserted", "b"]
        res = detect_unchanged(old, new)
        self.assertEqual(res.mapping, {1: 1, 2: 3})
        self.assertEqual(res.left_list, [])
        self.assertEqual(res.right_list, [2])

    def test_deletion_goes_to_left_list(self):
        old = ["a", "deleted", "b"]
        new = ["a", "b"]
        res = detect_unchanged(old, new)
        self.assertEqual(res.mapping, {1: 1, 3: 2})
        self.assertEqual(res.left_list, [2])
        self.assertEqual(res.right_list, [])

    def test_slide_filereader_example(self):
        old = [
            "public void fileReader(String path){",
            "FileReader fr = new FileReader(path);",
            "LineReader r = new LineReader(fr);",
            "String line  = null;",
            "while(line = lr.readLine()){",
            'System.out.println("line: "+line) ;',
            "}",
            "}",
        ]
        new = [
            "public void fileReader(String path){",
            "//Change the reader",
            "FileReader fr = new FileReader(path);",
            "BufferedReader r = new BufferedReader(fr);",
            "String line  = null;",
            "while(line = r.readLine()){",
            'System.out.println("line: "+line);',
            "} fr.close();",
            "}",
        ]
        res = detect_unchanged(old, new)
        # unchanged anchors: signature, FileReader line, String line, final }
        self.assertEqual(res.mapping, {1: 1, 2: 3, 4: 5, 7: 9})
        # changed old lines (LineReader, while, println, inner }) -> left list
        self.assertEqual(res.left_list, [3, 5, 6, 8])
        # added/changed new lines -> right list
        self.assertEqual(res.right_list, [2, 4, 6, 7, 8])


if __name__ == "__main__":
    unittest.main()
