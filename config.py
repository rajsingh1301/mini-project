"""Configuration settings for Real-Time Actionable Guidance System.
"""

from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent

# Camera Settings
CAMERA_INDEX = 0             # 0 for default laptop webcam, 1 for external
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30

# Detection Settings
MODEL_NAME = "yolov8n.pt"    # YOLOv8 nano: lightweight & fast
CONF_THRESHOLD = 0.45        # Minimum confidence threshold
IOU_THRESHOLD = 0.45

# Important obstacle & hazard classes (COCO dataset mappings)
# Priority weights (higher means higher hazard risk)
PRIORITY_CLASSES = {
    "person": 0.8,
    "bicycle": 0.9,
    "car": 1.0,
    "motorcycle": 1.0,
    "bus": 1.0,
    "truck": 1.0,
    "stop sign": 0.9,
    "chair": 0.6,
    "couch": 0.6,
    "dining table": 0.6,
    "bed": 0.5,
    "door": 0.7,
    "stairs": 1.0,
    "bottle": 0.3,
    "backpack": 0.4,
    "suitcase": 0.5,
}

# Spatial Grid Sector Thresholds (horizontal partition of frame)
LEFT_SECTOR_RATIO = 0.35     # [0, 0.35) -> Left
RIGHT_SECTOR_RATIO = 0.65    # (0.65, 1.0] -> Right
# [0.35, 0.65] -> Center / Ahead

# Proximity Thresholds (normalized bounding box area = (w*h) / (frame_w*frame_h))
IMMEDIATE_PROXIMITY_THRESHOLD = 0.20   # Very close (< 1 meter approx) -> Critical / STOP
NEAR_PROXIMITY_THRESHOLD = 0.08        # Moderate distance (1-2.5 meters)
FAR_PROXIMITY_THRESHOLD = 0.03         # Safe distance (> 2.5 meters)

# TTS Audio Settings
TTS_RATE = 190               # Words per minute (180-200 is clear and fast)
TTS_VOLUME = 1.0             # 0.0 to 1.0
AUDIO_THROTTLE_SECONDS = 2.0 # Minimum seconds between repeating same class in same sector
CRITICAL_OVERRIDE_SECONDS = 0.8 # Shorter interval for emergency "STOP" warnings
