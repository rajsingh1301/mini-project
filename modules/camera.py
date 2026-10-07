"""Camera capture module with FPS tracking and frame resizing.
"""

import time
import cv2
import numpy as np


class VideoStream:
    def __init__(self, src=0, width=640, height=480):
        self.src = src
        self.width = width
        self.height = height
        self.cap = None
        self.fps_start_time = time.time()
        self.fps_frame_counter = 0
        self.current_fps = 0.0

    def start(self):
        self.cap = cv2.VideoCapture(self.src)
        if not self.cap.isOpened():
            # Try index 1 if 0 fails
            self.cap = cv2.VideoCapture(1)
        
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Low latency buffer
            return True
        return False

    def read(self):
        if self.cap is None or not self.cap.isOpened():
            return False, None
        ret, frame = self.cap.read()
        if not ret:
            return False, None

        # Resize if camera did not apply hardware resolution
        h, w = frame.shape[:2]
        if w != self.width or h != self.height:
            frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_LINEAR)

        # Update FPS calculation
        self.fps_frame_counter += 1
        elapsed = time.time() - self.fps_start_time
        if elapsed >= 1.0:
            self.current_fps = round(self.fps_frame_counter / elapsed, 1)
            self.fps_frame_counter = 0
            self.fps_start_time = time.time()

        return True, frame

    def get_fps(self):
        return self.current_fps

    def stop(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()
