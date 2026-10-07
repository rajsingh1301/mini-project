"""Benchmark script for Measuring Detection Latency, Decision Latency, and FPS.
Outputs tabular metrics directly usable in the Research Paper!
"""

import sys
import time
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from modules.detector import ObstacleDetector
from modules.instruction import InstructionGenerator


def run_benchmark(iterations: int = 30):
    print("=" * 60)
    print(f"Running System Benchmark ({iterations} iterations)...")
    print("=" * 60)

    # 1. Initialize detector
    t0 = time.time()
    detector = ObstacleDetector()
    load_time = (time.time() - t0) * 1000
    print(f"Model initialization time: {load_time:.2f} ms")

    instruction_engine = InstructionGenerator()

    # Generate synthetic frames representing typical indoor scenes
    det_latencies = []
    engine_latencies = []
    total_latencies = []

    # Warmup
    dummy = np.zeros((config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), dtype=np.uint8)
    detector.detect(dummy)

    for i in range(iterations):
        frame = np.random.randint(0, 255, (config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), dtype=np.uint8)

        t_start = time.time()

        # Detection stage
        t_det_start = time.time()
        detections = detector.detect(frame)
        det_time = (time.time() - t_det_start) * 1000

        # Decision stage
        t_eng_start = time.time()
        directive = instruction_engine.generate_instruction(detections)
        eng_time = (time.time() - t_eng_start) * 1000

        total_time = (time.time() - t_start) * 1000

        det_latencies.append(det_time)
        engine_latencies.append(eng_time)
        total_latencies.append(total_time)

    avg_det = np.mean(det_latencies)
    avg_eng = np.mean(engine_latencies)
    avg_total = np.mean(total_latencies)
    theoretical_fps = 1000.0 / avg_total

    print("\n" + "-" * 40)
    print("BENCHMARK RESULTS (FOR RESEARCH PAPER)")
    print("-" * 40)
    print(f"YOLOv8 Nano Inference Latency : {avg_det:.2f} ms (Std: {np.std(det_latencies):.2f} ms)")
    print(f"HRI Decision Engine Latency   : {avg_eng:.2f} ms (Std: {np.std(engine_latencies):.2f} ms)")
    print(f"Total Pipeline Processing Time: {avg_total:.2f} ms")
    print(f"Achieved Throughput           : {theoretical_fps:.1f} FPS")
    print("-" * 40)


if __name__ == "__main__":
    run_benchmark(iterations=25)
