"""Configuration settings for Real-Time Actionable Guidance System.
"""

from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"

# Camera Settings
CAMERA_INDEX = 0             # 0 for default laptop webcam, 1 for external
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30

# Inference device: None picks automatically (CUDA GPU, then Apple "mps", then CPU)
DEVICE = None

# Detection Settings (general obstacles, COCO weights)
MODEL_NAME = "yolov8n.pt"    # YOLOv8 nano: lightweight & fast
CONF_THRESHOLD = 0.45        # Minimum confidence threshold
IOU_THRESHOLD = 0.45

# Structure model: custom weights for doors and stairs, which COCO does not have.
# Trained by training/train.py on Open Images. Skipped if the file is missing.
STRUCTURE_MODEL = MODELS_DIR / "door_stairs.pt"
STRUCTURE_CLASSES = ["door", "stairs"]   # Index order of the trained model
STRUCTURE_CONF = {"door": 0.45, "stairs": 0.40}
STRUCTURE_EVERY_N_FRAMES = 2  # Run it on every Nth frame and reuse the result in between

# Important obstacle & hazard classes. Priority weights (higher means higher hazard risk)
PRIORITY_CLASSES = {
    "stairs": 1.2,           # Fall risk: highest weight
    "person": 0.8,
    "bicycle": 0.9,
    "car": 1.0,
    "motorcycle": 1.0,
    "bus": 1.0,
    "truck": 1.0,
    "stop sign": 0.9,
    "door": 0.5,
    "chair": 0.6,
    "couch": 0.6,
    "dining table": 0.6,
    "bench": 0.6,
    "bed": 0.5,
    "potted plant": 0.5,
    "fire hydrant": 0.6,
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

# Floor-level hazards (stairs) are wide but flat, so box area says little about
# distance. For them, proximity comes from how low the box reaches in the frame.
FLOOR_CLASSES = {"stairs"}
FLOOR_IMMEDIATE_BOTTOM = 0.92          # Box bottom below 92% of frame height -> immediate
FLOOR_NEAR_BOTTOM = 0.75

# Tracking (frame-to-frame matching of the same object)
TRACK_MATCH_IOU = 0.3        # Minimum overlap to treat two boxes as the same object
TRACK_MAX_AGE_SECONDS = 0.7  # Forget a track not seen for this long
CONFIRM_HITS = 2             # Frames an object must be seen before it is announced
APPROACH_RATE = 0.06         # Box area growth per second (area ratio units) that means "approaching"
APPROACH_SMOOTHING = 0.5     # EMA factor for the growth rate (0..1, higher reacts faster)

# TTS Audio Settings
TTS_RATE = 190               # Words per minute (180-200 is clear and fast)
TTS_VOLUME = 1.0             # 0.0 to 1.0
AUDIO_THROTTLE_SECONDS = 4.0 # Minimum seconds between repeating same class in same sector
CRITICAL_OVERRIDE_SECONDS = 4.0 # Shorter interval for emergency "STOP" warnings
FAR_THROTTLE_SECONDS = 8.0   # Distant objects ahead are repeated less often
MIN_GAP_SECONDS = 2.0        # Minimum seconds between any two non-emergency announcements
PATH_CLEAR_AFTER_SECONDS = 3.0  # Say "Path clear" once the way ahead stays empty this long after a warning

# OCR Settings
# OCR is not part of the walking loop: it runs on request (`r` key, Read button)
# or in the web app's Read mode, which reads a high-resolution frame every few seconds.
OCR_LANGUAGES = ["en"]       # Add "hi" for Hindi boards (larger model, slower)
OCR_MIN_CONFIDENCE = 0.35
OCR_MAX_CHARACTERS = 300
OCR_MAX_SIDE = 1600          # Downscale larger photos to this before OCR
OCR_MIN_SIDE = 960           # Upscale smaller frames to this so small print stays readable
OCR_RETRY_SCALE = 1.5        # Contrast-enhanced second pass (only when the first finds nothing)
OCR_BLUR_THRESHOLD = 60.0    # Laplacian variance below this means the photo is blurry
OCR_DARK_THRESHOLD = 50      # Mean brightness (0-255) below this means too dark
OCR_EDGE_MARGIN = 0.03       # Text this close to the frame edge is probably cut off
OCR_SMALL_TEXT_HEIGHT = 0.035  # Median line height (fraction of frame) below this -> move closer
OCR_MODEL_DIR = MODELS_DIR / "easyocr"
OCR_USER_NETWORK_DIR = OCR_MODEL_DIR / "user_network"

# Web server
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
CERT_DIR = BASE_DIR / "certs"  # Self-signed HTTPS certificate so phones can use the camera
