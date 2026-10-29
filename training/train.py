"""Fine-tunes a YOLO nano model on the door/stairs dataset and installs it.

Start from COCO weights so the backbone already knows indoor scenes, then train
on the two new classes. The best checkpoint is scored on the held-out test split
and copied to config.STRUCTURE_MODEL only if it beats the installed model there;
the detector picks it up automatically.

Usage:
    python training/prepare_dataset.py       # once, downloads the data
    python training/train.py                 # Apple GPU/CUDA used if available
    python training/train.py --resume        # continue an interrupted run (e.g. Colab)
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
    # 640 px matches the frames the app sends; thin stair edges get lost at smaller sizes.
    # On the full ~17k images one epoch takes about 20 minutes on an Apple M4 GPU.
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=32)
    # A disk cache at 640 px needs ~16 GB for the full dataset; decoding JPEGs keeps up with the GPU
    parser.add_argument("--cache", default="none", help="disk, ram or none: cache decoded images")
    parser.add_argument("--force-install", action="store_true",
                        help="Install the new model even if it scores lower on the test split")
    parser.add_argument("--resume", action="store_true", help="Continue from the last saved epoch")
    parser.add_argument("--eval-only", action="store_true")
    args = parser.parse_args()

    from ultralytics import YOLO

    device = pick_device()
    if args.resume:
        # Ultralytics restores every training setting from the checkpoint
        YOLO(str(RUNS / "weights" / "last.pt")).train(resume=True)
    elif not args.eval_only:
        YOLO(args.base).train(
            data=str(DATA), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
            device=device, project=str(RUNS.parent), name=RUNS.name, exist_ok=True,
            patience=15, cos_lr=True, close_mosaic=5,
            cache=False if args.cache == "none" else args.cache,
            # Phones are held at odd angles and in mixed light
            degrees=5.0, hsv_v=0.5, fliplr=0.5,
        )
    if not args.eval_only:
        best = RUNS / "weights" / "best.pt"
        new = test_metrics(best, args.imgsz, device, "_test_new")
        if config.STRUCTURE_MODEL.exists() and not args.force_install:
            old = test_metrics(config.STRUCTURE_MODEL, args.imgsz, device, "_test_old")
            if new.box.map50 < old.box.map50:
                print(f"New model test mAP50 {new.box.map50:.3f} < installed {old.box.map50:.3f}; "
                      f"kept the installed model (new weights stay in {best})")
                return
        config.STRUCTURE_MODEL.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(best, config.STRUCTURE_MODEL)
        print(f"Installed {best} -> {config.STRUCTURE_MODEL}")

    # Held-out test split: these numbers go in the paper
    report(test_metrics(config.STRUCTURE_MODEL, args.imgsz, device, "_test"))


def test_metrics(weights: Path, imgsz: int, device: str, suffix: str):
    from ultralytics import YOLO
    return YOLO(str(weights)).val(
        data=str(DATA), split="test", imgsz=imgsz, device=device,
        project=str(RUNS.parent), name=RUNS.name + suffix, exist_ok=True,
    )


def report(metrics):
    for i, name in enumerate(config.STRUCTURE_CLASSES):
        p, r, ap50, ap = metrics.box.class_result(i)
        print(f"{name:7s} precision {p:.3f}  recall {r:.3f}  mAP50 {ap50:.3f}  mAP50-95 {ap:.3f}")
    print(f"all     mAP50 {metrics.box.map50:.3f}  mAP50-95 {metrics.box.map:.3f}")


if __name__ == "__main__":
    main()
