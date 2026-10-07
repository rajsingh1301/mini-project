"""Main application for Real-Time Actionable Guidance for the Visually Impaired.
"""

import sys
import time
import cv2
import numpy as np

import config
from modules.camera import VideoStream
from modules.detector import ObstacleDetector
from modules.instruction import InstructionGenerator
from modules.tts_engine import TTSEngine


def draw_hud(frame, detections, active_instruction, fps, latency_ms):
    """Renders visual Head-Up Display (HUD) with sector lines, bounding boxes,
    and latency metrics for demonstration and debugging.
    """
    h, w = frame.shape[:2]

    # 1. Draw Sector Dividers (dashed or subtle vertical lines)
    left_x = int(w * config.LEFT_SECTOR_RATIO)
    right_x = int(w * config.RIGHT_SECTOR_RATIO)

    cv2.line(frame, (left_x, 0), (left_x, h), (180, 180, 180), 1)
    cv2.line(frame, (right_x, 0), (right_x, h), (180, 180, 180), 1)

    # Sector labels at bottom
    cv2.putText(frame, "LEFT", (20, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(frame, "PATH (AHEAD)", (left_x + 30, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    cv2.putText(frame, "RIGHT", (right_x + 20, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # 2. Draw Detections
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        area_ratio = det["area_ratio"]
        cls_name = det["class_name"]
        conf = det["confidence"]

        # Color based on proximity: Red = Immediate, Yellow = Near, Green = Far
        if area_ratio >= config.IMMEDIATE_PROXIMITY_THRESHOLD:
            color = (0, 0, 255)      # Red (Critical)
            thickness = 3
        elif area_ratio >= config.NEAR_PROXIMITY_THRESHOLD:
            color = (0, 215, 255)    # Amber/Yellow
            thickness = 2
        else:
            color = (0, 255, 120)    # Green (Safe)
            thickness = 1

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
        label = f"{cls_name} {int(conf*100)}%"
        cv2.putText(frame, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

    # 3. Top Status Banner (Spoken Directive)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 55), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    # Directive text
    status_text = f"Action: {active_instruction.upper()}"
    banner_color = (0, 255, 255) if "STOP" not in active_instruction.upper() else (0, 0, 255)
    cv2.putText(frame, status_text, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.75, banner_color, 2)

    # Metrics (FPS & Latency)
    metrics_text = f"FPS: {fps} | Latency: {int(latency_ms)}ms"
    cv2.putText(frame, metrics_text, (w - 220, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    return frame


def create_simulated_frame(frame_counter):
    """Generates a synthetic camera test frame if hardware camera is unavailable."""
    frame = np.zeros((config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), dtype=np.uint8)
    # Background gradient
    for y in range(config.FRAME_HEIGHT):
        frame[y, :] = [40, 40, int(40 + 60 * (y / config.FRAME_HEIGHT))]

    # Moving synthetic obstacle to test detector
    cx = int(config.FRAME_WIDTH * (0.5 + 0.3 * np.sin(frame_counter * 0.05)))
    cy = int(config.FRAME_HEIGHT * 0.6)
    radius = int(40 + 20 * np.sin(frame_counter * 0.03))
    cv2.circle(frame, (cx, cy), radius, (200, 200, 200), -1)
    cv2.putText(frame, "SIMULATED FEED (No camera found)", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 180, 255), 2)
    return frame


def main():
    print("=" * 60)
    print("Real-Time Actionable Guidance for the Visually Impaired")
    print("Initializing components...")
    print("=" * 60)

    # 1. Initialize Camera
    camera = VideoStream(src=config.CAMERA_INDEX, width=config.FRAME_WIDTH, height=config.FRAME_HEIGHT)
    cam_available = camera.start()
    if not cam_available:
        print("[Warning] Hardware camera not available. Running in simulated camera feed mode.")

    # 2. Initialize Models & Engines
    print("Loading YOLOv8 model...")
    detector = ObstacleDetector()
    instruction_engine = InstructionGenerator()
    tts = TTSEngine()

    print("System active! Press 'q' in the video window or Ctrl+C in terminal to exit.")
    tts.speak("Guidance system active")

    frame_counter = 0
    current_active_directive = "Path clear"

    try:
        while True:
            t_start = time.time()

            # Step 1: Capture frame
            if cam_available:
                success, frame = camera.read()
                if not success:
                    time.sleep(0.01)
                    continue
            else:
                frame = create_simulated_frame(frame_counter)
                time.sleep(0.033) # Simulate ~30 FPS

            frame_counter += 1

            # Step 2: Obstacle Detection
            t_det_start = time.time()
            detections = detector.detect(frame)
            det_time = (time.time() - t_det_start) * 1000

            # Step 3: Instruction & Prioritization Decision
            spoken_instruction = instruction_engine.generate_instruction(detections)
            if spoken_instruction:
                current_active_directive = spoken_instruction
                is_emergency = "stop" in spoken_instruction.lower()
                tts.speak(spoken_instruction, priority=is_emergency)
            elif not detections:
                current_active_directive = "Path clear"

            # Step 4: Calculate Metrics
            total_latency = (time.time() - t_start) * 1000
            current_fps = camera.get_fps() if cam_available else round(1000.0 / max(1.0, total_latency), 1)

            # Step 5: Render Visual HUD
            frame_annotated = draw_hud(
                frame,
                detections,
                current_active_directive,
                current_fps,
                total_latency
            )

            cv2.imshow("Actionable Guidance System (Prototype)", frame_annotated)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

    except KeyboardInterrupt:
        print("\nStopping guidance system...")
    finally:
        camera.stop()
        tts.stop()
        cv2.destroyAllWindows()
        print("System shutdown complete.")


if __name__ == "__main__":
    main()
