"""Builds a YOLO-format door/stairs dataset from Open Images V7.

Streams the official bounding-box CSVs (only door and stairs rows are kept),
then downloads the matching images in parallel and writes YOLO labels.

The official validation split has only 36 stairs images, too few to pick the
best checkpoint, so part of the training pool is moved into val (half with
stairs). The official test split is kept as is so models stay comparable.

Usage:
    python training/prepare_dataset.py                 # all ~17k train images
    python training/prepare_dataset.py --train 6000    # smaller, faster run
"""

import argparse
import csv
import io
import random
import shutil
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
    with_stairs = sorted(k for k, v in boxes.items() if any(b[0] == 1 for b in v))
    door_only = sorted(k for k, v in boxes.items() if all(b[0] == 0 for b in v))
    rng.shuffle(with_stairs)
    rng.shuffle(door_only)
    stairs_take = min(len(with_stairs), limit // 2)
    chosen = with_stairs[:stairs_take] + door_only[: limit - stairs_take]
    return chosen


def download(split: str, image_id: str, img_dir: Path, pool: Path) -> bool:
    dest = img_dir / f"{image_id}.jpg"
    if dest.exists():
        return True
    kept = pool / dest.name
    if kept.exists():
        kept.rename(dest)
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


def reset_output(root: Path) -> Path:
    """Moves images from earlier runs into a pool (reused, not downloaded again)
    and deletes old labels and caches, so no image can leak between splits."""
    pool = root / "images" / "pool"
    pool.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val", "test"):
        for img in (root / "images" / split).glob("*.jpg"):
            img.rename(pool / img.name)
        for stale in (root / "images" / split).glob("*.npy"):
            stale.unlink()  # Disk cache made at another image size
        shutil.rmtree(root / "labels" / split, ignore_errors=True)
    for stale in (root / "labels").glob("*.cache"):
        stale.unlink()
    return pool


def build_split(out: str, parts: list, root: Path, pool: Path):
    """parts: (Open Images split, image ids, boxes) tuples that all go into `out`."""
    img_dir, lbl_dir = root / "images" / out, root / "labels" / out
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    counts, saved = [0, 0], 0
    for source, chosen, boxes in parts:
        print(f"[{out}] fetching {len(chosen)} images from Open Images {source}...")
        with ThreadPoolExecutor(max_workers=32) as executor:
            ok = list(executor.map(lambda i: download(source, i, img_dir, pool), chosen))
        for image_id, good in zip(chosen, ok):
            if not good:
                continue
            saved += 1
            lines = []
            for cls, cx, cy, w, h in boxes[image_id]:
                counts[cls] += 1
                lines.append(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            (lbl_dir / f"{image_id}.txt").write_text("\n".join(lines) + "\n")
    print(f"[{out}] saved {saved} images: {counts[0]} door boxes, {counts[1]} stairs boxes")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=int, default=20000, help="Training pool size (default: all)")
    parser.add_argument("--val-from-train", type=int, default=800,
                        help="Images moved from the training pool to val, half with stairs")
    parser.add_argument("--out", type=Path, default=config.BASE_DIR / "datasets" / "door_stairs")
    args = parser.parse_args()

    cache = args.out.parent / "openimages_raw"
    cache.mkdir(parents=True, exist_ok=True)
    train_boxes = stream_boxes("train", cache)
    val_boxes = stream_boxes("validation", cache)
    test_boxes = stream_boxes("test", cache)

    pool_ids = pick_balanced(train_boxes, args.train)
    extra_val = pick_balanced({k: train_boxes[k] for k in pool_ids}, args.val_from_train, seed=1)
    train_ids = sorted(set(pool_ids) - set(extra_val))

    pool = reset_output(args.out)
    build_split("test", [("test", sorted(test_boxes), test_boxes)], args.out, pool)
    build_split("val", [("validation", sorted(val_boxes), val_boxes), ("train", extra_val, train_boxes)],
                args.out, pool)
    build_split("train", [("train", train_ids, train_boxes)], args.out, pool)
    shutil.rmtree(pool)

    names = "\n".join(f"  {i}: {n}" for i, n in enumerate(config.STRUCTURE_CLASSES))
    (args.out / "data.yaml").write_text(
        f"path: {args.out}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n{names}\n"
    )
    print(f"Dataset ready: {args.out / 'data.yaml'}")


if __name__ == "__main__":
    main()
