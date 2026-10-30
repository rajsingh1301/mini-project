"""Main application for Real-Time Actionable Guidance for the Visually Impaired.
"""

import argparse
import sys
import time
import cv2
import numpy as np

import config
from modules.camera import VideoStream
from modules.detector import ObstacleDetector
from modules.guidance import GuidanceSession
from modules import phrases
from modules.ocr_reader import TextReader
from modules.sign_interpreter import SignInterpreter
from modules.tts_engine import TTSEngine


def draw_hud(frame, detections, active_instruction, fps, latency_ms, proximity_of):
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
        cls_name = det["class_name"] + (f" {det['stairs_dir']}" if det.get("stairs_dir") else "")
        conf = det["confidence"]

        # Color based on proximity: Red = Immediate, Yellow = Near, Green = Far
        proximity = proximity_of(det)
        if proximity == "immediate":
            color = (0, 0, 255)      # Red (Critical)
            thickness = 3
        elif proximity == "near":
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
    metrics_text = f"FPS: {fps} | Processing: {int(latency_ms)}ms"
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
    cv2.putText(frame, "NO CAMERA FOUND - CONNECT CAMERA FOR LIVE DETECTION", (25, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 180, 255), 2)
    return frame


def hud_text(text, result=None):
    """OpenCV's built-in font cannot draw Devanagari, so the HUD shows an ASCII summary
    of non-English phrases (they are still spoken in full)."""
    if text.isascii():
        return text
    kind = (result or {}).get("alert") or ("clear" if (result or {}).get("clear") else "info")
    return f"[spoken in {phrases.normalize(config.LANGUAGE)}] {kind}"


def main():
    parser = argparse.ArgumentParser(description="Guide Eye desktop demo")
    parser.add_argument("--lang", default=config.LANGUAGE, choices=phrases.LANGUAGES,
                        help="Language of spoken instructions (default: %(default)s)")
    lang = parser.parse_args().lang
    config.LANGUAGE = lang  # HUD helper and TTS read it

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
    if not detector.has_structure:
        print("[Info] Door/stairs model not found. Train it with: python training/train.py")
    session = GuidanceSession(detector, lang)
    text_reader = TextReader()
    signs = SignInterpreter()
    tts = TTSEngine(lang=lang)

    print("System active! Press 'r' to read a sign, 'q' to exit.")
    tts.speak({"en": "Guidance system active", "hi": "गाइडेंस चालू है"}.get(lang, "Guidance system active"))

    frame_counter = 0
    current_active_directive = hud_text(phrases.path_clear(lang))

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

            # Step 2 + 3: Detection, tracking and instruction decision
            # The fallback image is only a visible status screen; do not imply
            # that the model can detect its synthetic circle as a real object.
            if cam_available:
                result = session.step(frame)
                detections, spoken_instruction = result["detections"], result["instruction"]
            else:
                detections, spoken_instruction = [], None
            if spoken_instruction:
                current_active_directive = hud_text(spoken_instruction, result)
                tts.speak(spoken_instruction, priority=result["emergency"])
            elif not detections:
                current_active_directive = hud_text(phrases.path_clear(lang)) if cam_available else "Camera unavailable"

            # Step 4: Calculate Metrics
            total_latency = (time.time() - t_start) * 1000
            current_fps = camera.get_fps() if cam_available else round(1000.0 / max(1.0, total_latency), 1)

            # Step 5: Render Visual HUD
            frame_annotated = draw_hud(
                frame,
                detections,
                current_active_directive,
                current_fps,
                total_latency,
                session.engine.proximity_of
            )

            cv2.imshow("Actionable Guidance System (Prototype)", frame_annotated)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            if key == ord('r'):
                print("[OCR] Reading current frame...")
                try:
                    reading = signs.explain(text_reader.read_scene(frame, lang),
                                            detector.detect(frame, include_structure=False), frame, lang)
                    current_active_directive = hud_text(f"Text: {reading['text']}") if reading["text"] else "No readable text"
                    print(f"[OCR] {reading['summary']}")
                    tts.speak(reading["summary"], priority=True)
                except RuntimeError as error:
                    current_active_directive = "OCR unavailable"
                    print(f"[OCR] {error}")

    except KeyboardInterrupt:
        print("\nStopping guidance system...")
    finally:
        camera.stop()
        tts.stop()
        cv2.destroyAllWindows()
        print("System shutdown complete.")


if __name__ == "__main__":
    main()
