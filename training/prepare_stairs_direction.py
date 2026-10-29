"""Builds the stairs up/down classification dataset from your own clips.

Record clips with the phone at chest height while walking towards a staircase
(photos work too), and sort them by place and direction:

    datasets/stairs_clips/<place>/up/*.mp4      walking to the bottom step
    datasets/stairs_clips/<place>/down/*.mp4    walking to the top step

Every frame of an "up" clip shows stairs going up, so nothing is labelled by hand:
the door/stairs model finds the staircase in each sampled frame and its crop is
saved under the clip's label. Whole places are held out for val and test, so the
scores show how the model does on staircases it has never seen.

Usage:
    python training/prepare_stairs_direction.py
    python training/prepare_stairs_direction.py --test-places library --val-places hostel
"""

import argparse
import random
import shutil
import sys
from collections import Counter
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from modules.detector import ObstacleDetector, crop_with_pad

CLIPS = config.BASE_DIR / "datasets" / "stairs_clips"
OUT = config.BASE_DIR / "datasets" / "stairs_direction"
LABELS = ("down", "up")
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".webm"}
IMAGE_EXT = {".jpg", ".jpeg", ".png"}


def split_places(places: list, test: list, val: list, seed: int = 0) -> dict:
    """place -> train/val/test. Unnamed places: ~20% test, ~15% val, at least one each."""
    if not test or not val:
        if len(places) < 3:
            sys.exit(f"Need clips from at least 3 places (found {len(places)}): one each to train, "
                     f"validate and test on a staircase the model has not seen.")
        rest = [p for p in places if p not in test + val]
        random.Random(seed).shuffle(rest)
        if not test:
            test = rest[:max(1, round(len(places) * 0.2))]
            rest = rest[len(test):]
        if not val:
            val = rest[:max(1, round(len(places) * 0.15))]
    return {p: "test" if p in test else "val" if p in val else "train" for p in places}


def frames(path: Path, fps: float):
    """Yields frames sampled at about `fps` per second (or the photo itself)."""
    if path.suffix.lower() in IMAGE_EXT:
        img = cv2.imread(str(path))
        if img is not None:
            yield img
        return
    cap = cv2.VideoCapture(str(path))
    step = max(1, round((cap.get(cv2.CAP_PROP_FPS) or 30) / fps))
    index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if index % step == 0:
            yield frame
        index += 1
    cap.release()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clips", type=Path, default=CLIPS)
    parser.add_argument("--fps", type=float, default=4.0, help="Frames sampled per second of video")
    parser.add_argument("--test-places", default="", help="Comma-separated place folders for test")
    parser.add_argument("--val-places", default="", help="Comma-separated place folders for val")
    args = parser.parse_args()

    places = sorted(p.name for p in args.clips.iterdir() if p.is_dir()) if args.clips.is_dir() else []
    if not places:
        sys.exit(f"No clips found. Put them in {args.clips}/<place>/up/ and {args.clips}/<place>/down/")
    split_of = split_places(places, [p for p in args.test_places.split(",") if p],
                            [p for p in args.val_places.split(",") if p])

    detector = ObstacleDetector(stairs_direction_model=None)
    if not detector.has_structure:
        sys.exit(f"The door/stairs model is missing ({config.STRUCTURE_MODEL}); it finds the stairs to crop.")

    shutil.rmtree(OUT, ignore_errors=True)
    saved, missed = Counter(), Counter()
    for place in places:
        split = split_of[place]
        for label in LABELS:
            out_dir = OUT / split / label
            out_dir.mkdir(parents=True, exist_ok=True)
            clips = sorted(f for f in (args.clips / place / label).glob("*")
                           if f.suffix.lower() in VIDEO_EXT | IMAGE_EXT)
            for clip in clips:
                for i, frame in enumerate(frames(clip, args.fps)):
                    stairs = [d for d in detector.detect_structure(frame) if d["class_name"] == "stairs"]
                    if not stairs:
                        missed[split, label] += 1
                        continue
                    best = max(stairs, key=lambda d: d["confidence"])
                    crop = crop_with_pad(frame, best["bbox"], config.STAIRS_DIRECTION_PAD)
                    cv2.imwrite(str(out_dir / f"{place}_{clip.stem}_{i:05d}.jpg"), crop)
                    saved[split, label] += 1
        print(f"{place:20s} -> {split}")

    print("\nsplit  label  crops  frames without stairs")
    for split in ("train", "val", "test"):
        for label in LABELS:
            print(f"{split:6s} {label:5s} {saved[split, label]:6d} {missed[split, label]:6d}")
            if not saved[split, label]:
                print(f"  warning: no {label} crops in {split}; add {label} clips to one of its places")
    print(f"Dataset ready: {OUT}")


if __name__ == "__main__":
    main()
