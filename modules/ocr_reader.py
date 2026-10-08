"""On-demand sign and label reader using EasyOCR.

The reader is loaded lazily because its model startup is heavier than the
object detector. This keeps the normal obstacle-guidance loop responsive.
"""

import re
from typing import List

import config


class TextReader:
    """Reads visible English text from one BGR OpenCV frame."""

    def __init__(self):
        self._reader = None

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
                )
            except Exception as error:
                raise RuntimeError(
                    "OCR model could not be loaded. Check the EasyOCR model "
                    "download, then press r again."
                ) from error
        return self._reader

    @staticmethod
    def clean_text(parts: List[str]) -> str:
        """Combines OCR fragments into a short phrase suitable for speech."""
        text = " ".join(part.strip() for part in parts if part and part.strip())
        text = re.sub(r"\s+", " ", text).strip()
        return text[: config.OCR_MAX_CHARACTERS].rstrip()

    def read(self, frame) -> str:
        """Return recognized text, or an empty string when no usable text exists."""
        reader = self._get_reader()
        # EasyOCR accepts OpenCV's BGR array directly.
        # paragraph=False keeps EasyOCR's stable three-field result format:
        # (bounding_box, text, confidence).
        results = reader.readtext(frame, detail=1, paragraph=False)
        accepted = [
            text for _box, text, confidence in results
            if confidence >= config.OCR_MIN_CONFIDENCE
        ]
        return self.clean_text(accepted)
