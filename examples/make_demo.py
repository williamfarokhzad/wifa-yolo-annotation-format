"""Generate three tiny fictional datasets without image-library dependencies."""
import argparse
from pathlib import Path
import struct
import zlib


def png(boxes):
    # Each rectangle is half open: x0 <= x < x1 and y0 <= y < y1.
    w, h = 640, 480
    rows = [bytearray(bytes((231, 238, 239)) * w) for _ in range(h)]
    for x0, y0, x1, y1, color in boxes:
        for y in range(max(y0, 0), min(y1, h)):
            left, right = max(x0, 0), min(x1, w)
            rows[y][left*3:right*3] = bytes(color) * (right-left)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(b"\x00" + row for row in rows)))
            + chunk(b"IEND", b""))


def generate(out):
    out.mkdir(exist_ok=False)  # Refuse to modify an existing directory.
    teal, orange = (14, 116, 118), (180, 83, 9)
    for case in ("clean", "broken", "ambiguous"):
        root = out / case
        images, labels = root / "images/train", root / "labels/train"
        images.mkdir(parents=True)
        labels.mkdir(parents=True)
        (root / "data.yaml").write_text(
            "train: images/train\nval: images/val\nnames:\n  0: bracket\n  1: washer\n", encoding="utf-8")
        # The extra val split is a distinct synthetic scene, not a duplicate.
        for parent in ("images", "labels"):
            (root / parent / "val").mkdir()
        (root / "images/val/frame.png").write_bytes(png([(240, 90, 400, 150, teal)]))
        (root / "labels/val/frame.txt").write_text("0 .5 .25 .25 .125\n", encoding="utf-8")
        if case == "clean":
            (images / "tray.png").write_bytes(png([(160, 120, 320, 240, teal),
                                                 (480, 300, 560, 360, orange)]))
            (labels / "tray.txt").write_text("0 .375 .375 .25 .25\n1 .8125 .6875 .125 .125\n",
                                              encoding="utf-8")
            (images / "background.png").write_bytes(png([]))
            (labels / "background.txt").touch()
        elif case == "broken":
            (images / "edge.png").write_bytes(png([(480, 120, 672, 240, teal)]))
            (labels / "edge.txt").write_text("0 .90 .375 .30 .25\n2 .50 .5 .25 .25\n",
                                             encoding="utf-8")
            (labels / "old_export.txt").write_text("0 .5 .5 .25 .25\n", encoding="utf-8")
        else:
            # This image contains a part; treating a missing annotation as negative would be wrong.
            (images / "unreviewed.png").write_bytes(png([(160, 120, 320, 240, teal)]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        generate(args.output)
    except FileExistsError:
        parser.exit(2, "Output already exists. Choose a fresh directory.\n")
