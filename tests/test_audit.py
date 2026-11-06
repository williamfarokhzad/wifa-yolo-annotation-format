import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from audit import audit, parse_box


class GeometryTests(unittest.TestCase):
    def test_non_square_fixture_matches_hand_calculated_pixels(self):
        cls, edges = parse_box("0 .375 .375 .25 .25", 2)
        self.assertEqual(cls, 0)
        self.assertEqual([e*n for e, n in zip(edges, (640, 480, 640, 480))],
                         [160, 120, 320, 240])

    def test_exact_edge_is_allowed(self):
        self.assertEqual(parse_box("1 .9 .5 .2 1", 2)[1],
                         (Fraction(4, 5), 0, 1, 1))

    def test_individually_valid_fields_can_cross_the_edge(self):
        with self.assertRaisesRegex(ValueError, "^bounds:"):
            parse_box("0 .9 .375 .30 .25", 2)

    def test_bad_shape_class_and_value_rejected(self):
        for row, code in [
            ("0 .5 .5 .25 .25 .95", "fields"), ("2 .5 .5 .25 .25", "class"),
            ("1.0 .5 .5 .25 .25", "class"), ("0 nan .5 .25 .25", "number"),
            ("0 240 .5 .25 .25", "range"), ("0 .5 .5 0 .25", "size"),
        ]:
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, f"^{code}:"):
                parse_box(row, 2)


class FilesystemTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "images/train/sub").mkdir(parents=True)
        (self.root / "labels/train/sub").mkdir(parents=True)

    def put(self, path, data=b""):
        (self.root / path).write_bytes(data)

    def test_mirrored_nested_paths_and_duplicate_rows(self):
        self.put("images/train/sub/a.jpg")
        self.put("labels/train/sub/a.txt", b"1 .5 .5 .2 .2\n\n1 0.50 .50 .20 .20\n")
        issues, images, boxes = audit(self.root, "train", 2)
        self.assertEqual((images, boxes), (1, 1))
        self.assertEqual(issues[0][:2], ("ERROR", "duplicate"))
        self.assertIn("sub/a.txt:3:", issues[0][2])

    def test_missing_and_explicit_background_have_different_status(self):
        self.put("images/train/missing.png")
        self.put("images/train/empty.png")
        self.put("labels/train/empty.txt")
        loose, images, boxes = audit(self.root, "train", 2)
        strict, _, _ = audit(self.root, "train", 2, True)
        self.assertEqual((images, boxes), (2, 0))
        self.assertEqual(loose, [("WARN", "missing_label", "images/train/missing.png")])
        self.assertEqual(strict, [("ERROR", "missing_label", "images/train/missing.png")])

    def test_orphan_and_ambiguous_stem_not_mispaired(self):
        self.put("images/train/a.png")
        self.put("images/train/a.jpg")
        self.put("labels/train/a.txt", b"0 .5 .5 .2 .2")
        self.put("labels/train/sub/a.txt", b"0 .5 .5 .2 .2")
        issues, images, boxes = audit(self.root, "train", 2)
        self.assertEqual((images, boxes), (2, 0))
        self.assertEqual([i[1] for i in issues], ["ambiguous_stem", "orphan_label"])

    def test_wrong_encoding_is_reported_and_files_are_unchanged(self):
        self.put("images/train/a.png")
        self.put("labels/train/a.txt", b"\xff")
        issues, _, _ = audit(self.root, "train", 2)
        self.assertEqual(issues[0][1], "unreadable")
        self.assertEqual((self.root / "labels/train/a.txt").read_bytes(), b"\xff")

    def test_empty_and_missing_splits_fail(self):
        self.assertEqual(audit(self.root, "train", 2)[0][0][1], "no_images")
        self.assertEqual(audit(self.root, "val", 2)[0][0][1], "no_split")

    def test_cli_flags_invalid_class_count(self):
        command = [sys.executable, "audit.py", str(self.root), "--classes", "0"]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--classes must be", result.stderr)


if __name__ == "__main__":
    unittest.main()
