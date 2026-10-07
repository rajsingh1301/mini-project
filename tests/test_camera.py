"""Standalone camera verification and FPS test.
"""

import sys
import time
import cv2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.camera import VideoStream
import config


def test_cam():
    print(f"Testing camera at index {config.CAMERA_INDEX}...")
    stream = VideoStream(src=config.CAMERA_INDEX, width=config.FRAME_WIDTH, height=config.FRAME_HEIGHT)
    ok = stream.start()
    if not ok:
        print("[FAIL] Could not access physical webcam. Check camera permissions or plug in USB webcam.")
        return

    print("[SUCCESS] Camera opened. Press 'q' to stop.")
    while True:
        ret, frame = stream.read()
        if not ret:
            break

        fps = stream.get_fps()
        cv2.putText(frame, f"FPS: {fps}", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow("Camera Test", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    stream.stop()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    test_cam()
