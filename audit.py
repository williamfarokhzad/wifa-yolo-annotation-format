"""Read-only preflight for plain YOLO detection labels in one split."""
import argparse
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
import re

IMAGE_EXT = {".png", ".jpg", ".jpeg"}
DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\Z")
CLASS = re.compile(r"[0-9]{1,9}\Z")


def parse_box(row, class_count):
    """Return (class_id, left/top/right/bottom), or an actionable error."""
    fields = row.split()
    if len(fields) != 5:
        raise ValueError("fields: expected five values for plain detection")
    cls, *parts = fields
    if not CLASS.fullmatch(cls) or int(cls) >= class_count:
        raise ValueError("class: expected a zero-based ID in the configured range")
    if any(len(p) > 32 or not DECIMAL.fullmatch(p) for p in parts):
        raise ValueError("number: use finite plain decimals, with at most 32 characters each")
    x, y, w, h = map(Fraction, parts)
    if any(p < 0 or p > 1 for p in (x, y, w, h)):
        raise ValueError("range: divide x/width by image width and y/height by image height")
    if not w or not h:
        raise ValueError("size: width and height must both be positive")
    edges = (x - w/2, y - h/2, x + w/2, y + h/2)
    if min(edges) < 0 or max(edges) > 1:
        raise ValueError("bounds: a reconstructed edge leaves the image")
    return int(cls), edges


def by_stem(root, extensions):
    items = defaultdict(list)
    for p in sorted(root.rglob("*")):
        if not p.is_symlink() and p.is_file() and p.suffix.lower() in extensions:
            items[p.relative_to(root).with_suffix("").as_posix()].append(p)
    return items


def audit(root, split, class_count, strict_missing=False):
    """Return (issues, image count, valid box count); do not change files."""
    images_dir, labels_dir = (root / name / split for name in ("images", "labels"))
    if not images_dir.is_dir():
        return [("ERROR", "no_split", "images/" + split)], 0, 0
    images, labels = by_stem(images_dir, IMAGE_EXT), by_stem(labels_dir, {".txt"})
    issues, valid = [], 0
    if not images:
        issues.append(("ERROR", "no_images", "images/" + split))
    for key in sorted(images.keys() | labels.keys()):
        pics, txt = images[key], labels[key]
        if len(pics) > 1 or len(txt) > 1:
            issues.append(("ERROR", "ambiguous_stem", key))
            continue
        if not pics:
            issues.append(("ERROR", "orphan_label", txt[0].relative_to(root).as_posix()))
            continue
        if not txt:
            issues.append(("ERROR" if strict_missing else "WARN", "missing_label",
                           pics[0].relative_to(root).as_posix()))
            continue
        rel = txt[0].relative_to(root).as_posix()
        try:
            lines = txt[0].read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            issues.append(("ERROR", "unreadable", rel))
            continue
        seen = set()
        for lineno, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                box = parse_box(line, class_count)
                if box in seen:
                    raise ValueError("duplicate: same class and geometry already in this file")
                seen.add(box)
                valid += 1
            except ValueError as exc:
                code, detail = str(exc).split(": ", 1)
                issues.append(("ERROR", code, f"{rel}:{lineno}: {detail}"))
    return issues, sum(map(len, images.values())), valid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--split", choices=("train", "val", "test"), default="train")
    parser.add_argument("--classes", type=int, required=True, help="number of classes in data.yaml")
    parser.add_argument("--strict-missing", action="store_true",
                        help="require a label file, which may be empty for a known negative")
    args = parser.parse_args()
    if not 1 <= args.classes <= 1_000_000_000:
        parser.error("--classes must be between 1 and 1000000000")
    issues, images, boxes = audit(args.root, args.split, args.classes, args.strict_missing)
    for level, code, detail in issues:
        print(f"{level} {code} {detail}")
    errors = sum(level == "ERROR" for level, _, _ in issues)
    print(f"images={images} valid_boxes={boxes} errors={errors} warnings={len(issues)-errors}")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
