"""Trains the stairs up/down classifier and installs it if it is accurate enough.

A YOLO nano classifier looks only at the stairs crop. It is scored on the test
places (staircases it never saw) and copied to config.STAIRS_DIRECTION_MODEL only
when its accuracy reaches config.STAIRS_DIRECTION_MIN_ACCURACY: a wrong "going
up" is worse than plain "stairs ahead".

Usage:
    python training/prepare_stairs_direction.py   # clips -> crops
    python training/train_stairs_direction.py
"""

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from modules.detector import pick_device

DATA = config.BASE_DIR / "datasets" / "stairs_direction"
RUNS = config.BASE_DIR / "runs" / "stairs_direction"


def evaluate(weights: Path, device: str) -> float:
    """Prints per-class accuracy and the share of confident answers; returns accuracy."""
    from ultralytics import YOLO
    model = YOLO(str(weights))
    total = correct = confident = confident_correct = 0
    for label_dir in sorted((DATA / "test").iterdir()):
        files = sorted(label_dir.glob("*.jpg"))
        hits = 0
        for i in range(0, len(files), 64):
            for res in model.predict([str(f) for f in files[i:i + 64]], imgsz=config.STAIRS_DIRECTION_IMGSZ,
                                     device=device, verbose=False):
                guess = res.names[int(res.probs.top1)]
                hits += guess == label_dir.name
                if float(res.probs.top1conf) >= config.STAIRS_DIRECTION_CONF:
                    confident += 1
                    confident_correct += guess == label_dir.name
        print(f"{label_dir.name:5s} accuracy {hits / max(1, len(files)):.3f}  ({hits}/{len(files)} crops)")
        total += len(files)
        correct += hits
    accuracy = correct / max(1, total)
    print(f"all   accuracy {accuracy:.3f}  ({correct}/{total} crops)")
    print(f"confident (>= {config.STAIRS_DIRECTION_CONF}) on {confident / max(1, total):.0%} of crops, "
          f"accuracy {confident_correct / max(1, confident):.3f} there")
    return accuracy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="yolo11n-cls.pt", help="Starting weights (ImageNet pretrained)")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--force-install", action="store_true",
                        help="Install even below STAIRS_DIRECTION_MIN_ACCURACY")
    parser.add_argument("--eval-only", action="store_true", help="Score the installed model")
    args = parser.parse_args()

    from ultralytics import YOLO

    device = pick_device()
    if args.eval_only:
        evaluate(config.STAIRS_DIRECTION_MODEL, device)
        return

    YOLO(args.base).train(
        data=str(DATA), epochs=args.epochs, imgsz=config.STAIRS_DIRECTION_IMGSZ, batch=args.batch,
        device=device, project=str(RUNS.parent), name=RUNS.name, exist_ok=True, patience=10,
        # Mirroring keeps the direction; a vertical flip would turn up into down
        fliplr=0.5, flipud=0.0,
    )
    best = RUNS / "weights" / "best.pt"
    accuracy = evaluate(best, device)
    if accuracy < config.STAIRS_DIRECTION_MIN_ACCURACY and not args.force_install:
        print(f"Test accuracy {accuracy:.3f} is below {config.STAIRS_DIRECTION_MIN_ACCURACY}; not installed. "
              f"Record more clips (more places, both directions) and train again.")
        return
    config.STAIRS_DIRECTION_MODEL.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(best, config.STAIRS_DIRECTION_MODEL)
    print(f"Installed {best} -> {config.STAIRS_DIRECTION_MODEL}")


if __name__ == "__main__":
    main()
