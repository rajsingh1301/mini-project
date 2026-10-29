"""Benchmark script for Measuring Detection Latency, Decision Latency, and FPS.
Outputs tabular metrics directly usable in the Research Paper!

Uses real photos (Ultralytics sample images) instead of random noise, so the
models actually find objects and the numbers reflect a realistic workload.
"""

import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from modules.detector import ObstacleDetector
from modules.guidance import GuidanceSession
from modules.instruction import InstructionGenerator
from modules.tracker import ObjectTracker


def sample_frames():
    from ultralytics.utils import ASSETS
    frames = []
    for path in sorted(ASSETS.glob("*.jpg")):
        img = cv2.imread(str(path))
        if img is not None:
            frames.append(cv2.resize(img, (config.FRAME_WIDTH, config.FRAME_HEIGHT)))
    return frames or [np.random.randint(0, 255, (config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), np.uint8)]


def timed(fn, *args, **kwargs):
    t = time.perf_counter()
    out = fn(*args, **kwargs)
    return out, (time.perf_counter() - t) * 1000


def report(name, values):
    print(f"{name:32s}: {np.mean(values):7.2f} ms (Std: {np.std(values):5.2f}, median {np.median(values):6.2f})")


def run_benchmark(iterations: int = 30):
    print("=" * 60)
    print(f"Running System Benchmark ({iterations} iterations)...")
    print("=" * 60)

    # 1. Initialize detector
    t0 = time.time()
    detector = ObstacleDetector()
    load_time = (time.time() - t0) * 1000
    print(f"Model initialization time: {load_time:.2f} ms  (device: {detector.device}, "
          f"door/stairs model: {'yes' if detector.has_structure else 'not installed'})")

    frames = sample_frames()
    # Warmup
    for f in frames:
        detector.detect(f)

    coco, structure, decision, session_ms = [], [], [], []
    tracker, engine = ObjectTracker(), InstructionGenerator()
    for i in range(iterations):
        frame = frames[i % len(frames)]
        dets, ms = timed(detector.detect, frame, include_structure=False)
        coco.append(ms)
        if detector.has_structure:
            more, ms = timed(detector.detect_structure, frame)
            structure.append(ms)
            dets += more
        t = time.perf_counter()
        tracker.update(dets, time.time())
        engine.generate_instruction(dets)
        decision.append((time.perf_counter() - t) * 1000)

    # Full per-frame pipeline as the app runs it (structure model every Nth frame)
    session = GuidanceSession(detector)
    for i in range(iterations):
        _, ms = timed(session.step, frames[i % len(frames)])
        session_ms.append(ms)

    print("\n" + "-" * 40)
    print("BENCHMARK RESULTS (FOR RESEARCH PAPER)")
    print("-" * 40)
    report(f"COCO detector ({config.MODEL_NAME})", coco)
    if structure:
        report("Door/stairs detector", structure)
    report("Tracker + HRI decision", decision)
    report("Full session step", session_ms)
    print(f"{'Achieved Throughput':32s}: {1000.0 / np.mean(session_ms):7.1f} FPS "
          f"(structure model every {config.STRUCTURE_EVERY_N_FRAMES} frames)")
    print("-" * 40)
    print("Excludes camera capture, JPEG transfer and speech start.")


if __name__ == "__main__":
    run_benchmark(iterations=60)
