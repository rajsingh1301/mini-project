"""Builds a YOLO-format door/stairs dataset from Open Images V7.

Streams the official bounding-box CSVs (only door and stairs rows are kept),
then downloads the matching images in parallel and writes YOLO labels.

Usage:
    python training/prepare_dataset.py --train 6000 --val 800 --test 800
"""

import argparse
import csv
import io
import random
import sys
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

# Open Images label id -> our class index (order must match config.STRUCTURE_CLASSES)
LABELS = {"/m/02dgv": 0, "/m/01lynh": 1}  # Door, Stairs
ANNOTATIONS = {
    "train": "https://storage.googleapis.com/openimages/v6/oidv6-train-annotations-bbox.csv",
    "validation": "https://storage.googleapis.com/openimages/v5/validation-annotations-bbox.csv",
    "test": "https://storage.googleapis.com/openimages/v5/test-annotations-bbox.csv",
}
IMAGE_URL = "https://s3.amazonaws.com/open-images-dataset/{split}/{image_id}.jpg"
OUT_SPLIT = {"train": "train", "validation": "val", "test": "test"}
MAX_SIDE = 640


def stream_boxes(split: str, cache: Path) -> dict:
    """Return image_id -> list of (cls, cx, cy, w, h); cached as a filtered CSV."""
    cached = cache / f"{split}-door-stairs.csv"
    if not cached.exists():
        print(f"[{split}] streaming annotations (large file, filtered on the fly)...")
        with urllib.request.urlopen(ANNOTATIONS[split]) as resp, open(cached, "w", newline="") as out:
            reader = csv.DictReader(io.TextIOWrapper(resp, encoding="utf-8"))
            writer = csv.writer(out)
            writer.writerow(["ImageID", "LabelName", "XMin", "XMax", "YMin", "YMax", "IsDepiction"])
            for row in reader:
                if row["LabelName"] in LABELS:
                    writer.writerow([row["ImageID"], row["LabelName"], row["XMin"], row["XMax"],
                                     row["YMin"], row["YMax"], row["IsDepiction"]])

    boxes, depicted = defaultdict(list), set()
    with open(cached, newline="") as f:
        for row in csv.DictReader(f):
            image_id = row["ImageID"]
            if row["IsDepiction"] == "1":
                # Drawings and posters of doors/stairs are not real hazards
                depicted.add(image_id)
                continue
            x1, x2, y1, y2 = (float(row[k]) for k in ("XMin", "XMax", "YMin", "YMax"))
            boxes[image_id].append((LABELS[row["LabelName"]], (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1))
    return {k: v for k, v in boxes.items() if k not in depicted}


def pick_balanced(boxes: dict, limit: int, seed: int = 0) -> list:
    """Pick up to `limit` images, half that contain stairs (the rarer class) first."""
    rng = random.Random(seed)
    with_stairs = [k for k, v in boxes.items() if any(b[0] == 1 for b in v)]
    door_only = [k for k, v in boxes.items() if all(b[0] == 0 for b in v)]
    rng.shuffle(with_stairs)
    rng.shuffle(door_only)
    stairs_take = min(len(with_stairs), limit // 2)
    chosen = with_stairs[:stairs_take] + door_only[: limit - stairs_take]
    return chosen


def download(split: str, image_id: str, img_dir: Path) -> bool:
    dest = img_dir / f"{image_id}.jpg"
    if dest.exists():
        return True
    try:
        with urllib.request.urlopen(IMAGE_URL.format(split=split, image_id=image_id), timeout=30) as resp:
            img = cv2.imdecode(np.frombuffer(resp.read(), np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        return False
    if img is None:
        return False
    h, w = img.shape[:2]
    scale = MAX_SIDE / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(dest), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return True


def build_split(split: str, limit: int, root: Path, cache: Path):
    boxes = stream_boxes(split, cache)
    chosen = pick_balanced(boxes, limit)
    out = OUT_SPLIT[split]
    img_dir, lbl_dir = root / "images" / out, root / "labels" / out
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    print(f"[{split}] {len(boxes)} usable images, downloading {len(chosen)}...")
    with ThreadPoolExecutor(max_workers=32) as pool:
        ok = list(pool.map(lambda i: download(split, i, img_dir), chosen))

    counts = [0, 0]
    for image_id, good in zip(chosen, ok):
        if not good:
            continue
        lines = []
        for cls, cx, cy, w, h in boxes[image_id]:
            counts[cls] += 1
            lines.append(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
        (lbl_dir / f"{image_id}.txt").write_text("\n".join(lines) + "\n")
    print(f"[{split}] saved {sum(ok)} images: {counts[0]} door boxes, {counts[1]} stairs boxes")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=int, default=6000)
    parser.add_argument("--val", type=int, default=800)
    parser.add_argument("--test", type=int, default=800)
    parser.add_argument("--out", type=Path, default=config.BASE_DIR / "datasets" / "door_stairs")
    args = parser.parse_args()

    cache = args.out.parent / "openimages_raw"
    cache.mkdir(parents=True, exist_ok=True)
    for split, limit in (("validation", args.val), ("test", args.test), ("train", args.train)):
        build_split(split, limit, args.out, cache)

    names = "\n".join(f"  {i}: {n}" for i, n in enumerate(config.STRUCTURE_CLASSES))
    (args.out / "data.yaml").write_text(
        f"path: {args.out}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n{names}\n"
    )
    print(f"Dataset ready: {args.out / 'data.yaml'}")


if __name__ == "__main__":
    main()
