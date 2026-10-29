"""Sign and label reader using EasyOCR.

Reads text in natural order (top to bottom, left to right) and also checks the
photo itself, so a blind user hears how to aim better: move closer, hold steady,
or move the phone towards text that is cut off at the edge.

The reader is loaded lazily because its model startup is heavier than the
object detector. This keeps the normal obstacle-guidance loop responsive.
"""

import re
import threading
from statistics import median
from typing import Any, Dict, List

import cv2
import numpy as np

import config


class TextReader:
    """Reads visible text from one BGR OpenCV frame."""

    def __init__(self):
        self._reader = None
        self._lock = threading.Lock()

    def _get_reader(self):
        if self._reader is None:
            try:
                import easyocr
            except ImportError as error:
                raise RuntimeError(
                    "EasyOCR is not installed. Run: pip install easyocr"
                ) from error
            # GPU=False keeps this dependable on ordinary laptops.
            try:
                self._reader = easyocr.Reader(
                    config.OCR_LANGUAGES,
                    gpu=False,
                    model_storage_directory=str(config.OCR_MODEL_DIR),
                    user_network_directory=str(config.OCR_USER_NETWORK_DIR),
                    verbose=False,
                )
            except Exception as error:
                raise RuntimeError(
                    "OCR model could not be loaded. Check the EasyOCR model "
                    "download, then try again."
                ) from error
        return self._reader

    def warm_up(self):
        """Loads the model ahead of time so the first real request is fast."""
        with self._lock:
            self._get_reader()

    @staticmethod
    def clean_text(parts: List[str]) -> str:
        """Combines OCR fragments into a short phrase suitable for speech."""
        text = " ".join(part.strip() for part in parts if part and part.strip())
        text = re.sub(r"\s+", " ", text).strip()
        return text[: config.OCR_MAX_CHARACTERS].rstrip()

    @staticmethod
    def image_quality(frame) -> Dict[str, Any]:
        """Blur (Laplacian variance) and brightness, measured at a fixed size."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        scale = 640.0 / max(h, w)
        small = cv2.resize(gray, (max(1, int(w * scale)), max(1, int(h * scale))))
        sharpness = float(cv2.Laplacian(small, cv2.CV_64F).var())
        brightness = float(small.mean())
        return {
            "sharpness": round(sharpness, 1),
            "brightness": round(brightness, 1),
            "blurry": sharpness < config.OCR_BLUR_THRESHOLD,
            "dark": brightness < config.OCR_DARK_THRESHOLD,
        }

    @staticmethod
    def prepare(frame):
        """Resizes so small print is big enough and huge photos stay fast."""
        h, w = frame.shape[:2]
        longest = max(h, w)
        if longest > config.OCR_MAX_SIDE:
            scale = config.OCR_MAX_SIDE / longest
        elif longest < config.OCR_MIN_SIDE:
            scale = config.OCR_MIN_SIDE / longest
        else:
            return frame
        interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
        return cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=interp)

    @staticmethod
    def keep(text: str, confidence: float) -> bool:
        """Drops low-confidence fragments and lone symbols that are usually noise."""
        stripped = text.strip()
        if confidence < config.OCR_MIN_CONFIDENCE or not re.search(r"\w", stripped):
            return False
        if len(stripped) == 1 and confidence < 0.7:
            return False
        return True

    @staticmethod
    def group_lines(items: List[Dict[str, Any]]) -> List[str]:
        """Orders words into lines: rows top to bottom, words left to right."""
        if not items:
            return []
        typical = median(it["h"] for it in items)
        rows: List[List[Dict[str, Any]]] = []
        for it in sorted(items, key=lambda i: i["cy"]):
            if rows and abs(it["cy"] - rows[-1][-1]["cy"]) <= 0.5 * typical:
                rows[-1].append(it)
            else:
                rows.append([it])
        lines = [TextReader.clean_text([i["text"] for i in sorted(row, key=lambda i: i["x1"])]) for row in rows]
        return [line for line in lines if line]

    @staticmethod
    def aiming_hints(items: List[Dict[str, Any]], width: int, height: int, quality: Dict[str, Any]) -> List[str]:
        """Spoken advice on how to point the camera for a better read."""
        hints = []
        if quality["dark"]:
            hints.append("It is too dark. Find more light.")
        if quality["blurry"]:
            hints.append("The picture is blurry. Hold the phone steady.")
        if not items:
            if not hints:
                hints.append("Point the phone at the sign, about one arm's length away.")
            return hints

        margin_x, margin_y = config.OCR_EDGE_MARGIN * width, config.OCR_EDGE_MARGIN * height
        x1 = min(i["x1"] for i in items)
        x2 = max(i["x2"] for i in items)
        y1 = min(i["y1"] for i in items)
        y2 = max(i["y2"] for i in items)
        cut = []
        if x1 <= margin_x:
            cut.append("left")
        if x2 >= width - margin_x:
            cut.append("right")
        if y1 <= margin_y:
            cut.append("up")
        if y2 >= height - margin_y:
            cut.append("down")
        if cut:
            hints.append(f"Text may be cut off. Move the phone {' and '.join(cut)}.")
        elif median(i["h"] for i in items) / height < config.OCR_SMALL_TEXT_HEIGHT:
            hints.append("The text is small. Move closer.")
        return hints

    @staticmethod
    def enhance(image):
        """Grayscale, upscaled, local-contrast boost: rescues engraved or faded text."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=config.OCR_RETRY_SCALE, fy=config.OCR_RETRY_SCALE,
                          interpolation=cv2.INTER_CUBIC)
        return cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)

    def _items(self, reader, image, scale: float = 1.0) -> List[Dict[str, Any]]:
        """Kept OCR fragments with boxes in `image / scale` coordinates."""
        # paragraph=False keeps EasyOCR's stable three-field result format:
        # (bounding_box, text, confidence).
        items = []
        for box, text, confidence in reader.readtext(image, detail=1, paragraph=False):
            if not self.keep(text, confidence):
                continue
            xs = [p[0] / scale for p in box]
            ys = [p[1] / scale for p in box]
            items.append({
                "text": text, "conf": float(confidence),
                "x1": min(xs), "x2": max(xs), "y1": min(ys), "y2": max(ys),
                "cy": (min(ys) + max(ys)) / 2, "h": max(ys) - min(ys),
            })
        return items

    def read_scene(self, frame) -> Dict[str, Any]:
        """Full read: lines of text, mean confidence, quality and aiming hints."""
        quality = self.image_quality(frame)
        image = self.prepare(frame)
        height, width = image.shape[:2]
        with self._lock:
            reader = self._get_reader()
            items = self._items(reader, image)
            if not items:
                # Second, slower pass only when the plain one found nothing: it helps
                # low-contrast signs but can hurt bold ones, so it is not the default
                items = self._items(reader, self.enhance(image), config.OCR_RETRY_SCALE)

        lines = self.group_lines(items)
        return {
            "text": self.clean_text(lines),
            "lines": lines,
            "confidence": round(float(np.mean([i["conf"] for i in items])), 2) if items else 0.0,
            "quality": quality,
            "hints": self.aiming_hints(items, width, height, quality),
        }

    def read(self, frame) -> str:
        """Return recognized text, or an empty string when no usable text exists."""
        return self.read_scene(frame)["text"]
