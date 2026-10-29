"""Fine-tunes a YOLO nano model on the door/stairs dataset and installs it.

Start from COCO weights so the backbone already knows indoor scenes, then train
on the two new classes. The best checkpoint is copied to config.STRUCTURE_MODEL,
where the detector picks it up automatically.

Usage:
    python training/prepare_dataset.py       # once, downloads the data
    python training/train.py                 # Apple GPU/CUDA used if available
    python training/train.py --eval-only     # test-split metrics for the paper
"""

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from modules.detector import pick_device

DATA = config.BASE_DIR / "datasets" / "door_stairs" / "data.yaml"
RUNS = config.BASE_DIR / "runs" / "door_stairs"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="yolo11n.pt", help="Starting weights (COCO pretrained)")
    # 25 epochs at 512 px take about two hours on an Apple M4 GPU; COCO weights converge fast
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--imgsz", type=int, default=512)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--cache", default="disk", help="disk, ram or none: cache decoded images")
    parser.add_argument("--eval-only", action="store_true")
    args = parser.parse_args()

    from ultralytics import YOLO

    device = pick_device()
    if not args.eval_only:
        model = YOLO(args.base)
        model.train(
            data=str(DATA), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
            device=device, project=str(RUNS.parent), name=RUNS.name, exist_ok=True,
            patience=10, cos_lr=True, close_mosaic=5,
            cache=False if args.cache == "none" else args.cache,
            # Phones are held at odd angles and in mixed light
            degrees=5.0, hsv_v=0.5, fliplr=0.5,
        )
        best = RUNS / "weights" / "best.pt"
        config.STRUCTURE_MODEL.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(best, config.STRUCTURE_MODEL)
        print(f"Installed {best} -> {config.STRUCTURE_MODEL}")

    # Held-out test split: these numbers go in the paper
    metrics = YOLO(str(config.STRUCTURE_MODEL)).val(
        data=str(DATA), split="test", imgsz=args.imgsz, device=device,
        project=str(RUNS.parent), name=RUNS.name + "_test", exist_ok=True,
    )
    for i, name in enumerate(config.STRUCTURE_CLASSES):
        p, r, ap50, ap = metrics.box.class_result(i)
        print(f"{name:7s} precision {p:.3f}  recall {r:.3f}  mAP50 {ap50:.3f}  mAP50-95 {ap:.3f}")
    print(f"all     mAP50 {metrics.box.map50:.3f}  mAP50-95 {metrics.box.map:.3f}")


if __name__ == "__main__":
    main()
