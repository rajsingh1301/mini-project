"""Unit tests for the text reader (EasyOCR replaced by a fake) and the sign interpreter.
"""

import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.ocr_reader import TextReader
from modules.sign_interpreter import SignInterpreter


def quad(x1, y1, x2, y2):
    return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]


class FakeEasyOCR:
    def __init__(self, results):
        self.results = results

    def readtext(self, image, **kwargs):
        return self.results


def textured_frame(h=720, w=960):
    """Sharp, bright frame so quality checks pass."""
    frame = np.full((h, w, 3), 200, np.uint8)
    for x in range(0, w, 8):
        cv2.line(frame, (x, 0), (x, h), (0, 0, 0), 1)
    return frame


class TestTextReader(unittest.TestCase):
    def reader_with(self, results):
        reader = TextReader()
        reader._reader = FakeEasyOCR(results)
        return reader

    def test_lines_are_read_top_to_bottom_left_to_right(self):
        reader = self.reader_with([
            (quad(500, 300, 700, 340), "Lab", 0.9),
            (quad(300, 200, 450, 240), "Room", 0.9),
            (quad(470, 205, 560, 245), "204", 0.95),
            (quad(300, 300, 480, 340), "Computer", 0.9),
        ])
        result = reader.read_scene(textured_frame())
        self.assertEqual(result["lines"], ["Room 204", "Computer Lab"])
        self.assertEqual(result["text"], "Room 204 Computer Lab")
        self.assertEqual(result["hints"], [])

    def test_hindi_uses_its_own_reader_and_hints(self):
        english, hindi = FakeEasyOCR([]), FakeEasyOCR([(quad(300, 200, 450, 240), "निकास", 0.9)])
        reader = TextReader()
        reader._reader = english
        reader._extra[("hi", "en")] = hindi
        self.assertEqual(reader.read_scene(textured_frame(), "hi")["text"], "निकास")
        self.assertEqual(reader.read_scene(textured_frame())["text"], "")
        # No text: hints in the asked language, plus language-independent codes
        out = reader.read_scene(textured_frame())
        self.assertEqual(out["hint_codes"], [("aim", [])])
        self.assertEqual(out["hints"], ["Point the phone at the sign, about one arm's length away."])

    def test_hindi_model_is_loaded_once_on_first_use(self):
        from unittest import mock
        reader = TextReader()
        with mock.patch.object(TextReader, "_load", return_value=FakeEasyOCR([])) as load:
            reader._get_reader("hi")
            reader._get_reader("hi")
            reader._get_reader("en")
        self.assertEqual([c.args[0] for c in load.call_args_list], [["hi", "en"], ["en"]])

    def test_noise_is_dropped(self):
        self.assertFalse(TextReader.keep("-", 0.99))
        self.assertFalse(TextReader.keep("x", 0.5))
        self.assertFalse(TextReader.keep("EXIT", 0.1))
        self.assertTrue(TextReader.keep("EXIT", 0.8))

    def test_cut_off_text_gives_direction_hint(self):
        reader = self.reader_with([(quad(700, 300, 960, 360), "Platform", 0.9)])
        hints = reader.read_scene(textured_frame())["hints"]
        self.assertTrue(any("move the phone right" in h.lower() for h in hints), hints)

    def test_small_text_hint(self):
        reader = self.reader_with([(quad(400, 300, 460, 310), "tiny", 0.9)])
        hints = reader.read_scene(textured_frame())["hints"]
        self.assertIn("The text is small. Move closer.", hints)

    def test_dark_and_blurry_frames(self):
        quality = TextReader.image_quality(np.full((480, 640, 3), 10, np.uint8))
        self.assertTrue(quality["dark"])
        self.assertTrue(quality["blurry"])
        reader = self.reader_with([])
        result = reader.read_scene(np.full((480, 640, 3), 10, np.uint8))
        self.assertEqual(result["text"], "")
        self.assertTrue(any("dark" in h for h in result["hints"]))

    def test_enhanced_retry_when_plain_pass_finds_nothing(self):
        class GrayOnly(FakeEasyOCR):
            def readtext(self, image, **kwargs):
                # Text is only legible after the contrast boost (2-D grayscale image)
                return self.results if image.ndim == 2 else []
        reader = TextReader()
        reader._reader = GrayOnly([(quad(450, 450, 750, 510), "SPANISH STEPS", 0.99)])
        result = reader.read_scene(textured_frame())
        self.assertEqual(result["text"], "SPANISH STEPS")
        self.assertEqual(result["hints"], [])  # boxes mapped back to frame scale, not cut off

    def test_prepare_resizes(self):
        self.assertEqual(max(TextReader.prepare(np.zeros((3000, 4000, 3), np.uint8)).shape[:2]), 1600)
        self.assertEqual(max(TextReader.prepare(np.zeros((240, 320, 3), np.uint8)).shape[:2]), 960)


class TestSignInterpreter(unittest.TestCase):
    def setUp(self):
        self.signs = SignInterpreter()

    def test_classify_common_signs(self):
        cases = {
            "EXIT": "exit", "Fire Exit": "exit", "NO ENTRY": "no_entry", "Do not enter": "no_entry",
            "Wet floor": "warning", "PUSH": "push", "Pull": "pull", "Ladies Toilet": "restroom",
            "STOP": "stop", "Bus Stop": "bus_stop", "Platform No. 3": "platform", "Lift": "lift",
            "Main Entrance": "entrance",
        }
        for text, kind in cases.items():
            with self.subTest(text=text):
                self.assertEqual(self.signs.classify(text)["kind"], kind)
        self.assertIsNone(self.signs.classify("Room 204 Computer Lab"))
        # "stop" inside a sentence is not a stop sign
        self.assertNotEqual((self.signs.classify("Please stop by the office") or {}).get("kind"), "stop")

    def test_explain_sign(self):
        out = self.signs.explain({"text": "EXIT", "lines": ["EXIT"], "hints": []})
        self.assertEqual(out["kind"], "exit")
        self.assertEqual(out["summary"], "Exit sign. It says: EXIT. It shows the way out.")

    def test_explain_plain_text_with_hint(self):
        out = self.signs.explain({"text": "Room 204", "lines": ["Room 204"], "hints": ["The text is small. Move closer."]})
        self.assertEqual(out["summary"], "It says: Room 204. The text is small. Move closer.")

    def test_explain_nothing(self):
        out = self.signs.explain({"text": "", "lines": [], "hints": ["It is too dark. Find more light."]})
        self.assertEqual(out["summary"], "No text found. It is too dark. Find more light.")

    def test_arrow(self):
        out = self.signs.explain({"text": "Toilets →", "lines": [], "hints": []})
        self.assertIn("The arrow points right.", out["summary"])

    def test_traffic_light_color(self):
        frame = np.zeros((300, 100, 3), np.uint8)
        cv2.circle(frame, (50, 50), 30, (0, 0, 255), -1)      # red lamp lit (BGR)
        self.assertEqual(SignInterpreter.traffic_light_color(frame, [0, 0, 100, 300]), "red")
        frame[:] = 0
        cv2.circle(frame, (50, 250), 30, (80, 255, 0), -1)    # green lamp lit
        self.assertEqual(SignInterpreter.traffic_light_color(frame, [0, 0, 100, 300]), "green")
        frame[:] = 0
        self.assertIsNone(SignInterpreter.traffic_light_color(frame, [0, 0, 100, 300]))

    def test_stop_sign_not_repeated(self):
        dets = [{"class_name": "stop sign", "bbox": [0, 0, 10, 10]}]
        out = self.signs.explain({"text": "STOP", "lines": ["STOP"], "hints": []}, dets, np.zeros((10, 10, 3), np.uint8))
        self.assertEqual(out["summary"].count("top sign"), 1)


if __name__ == "__main__":
    unittest.main()
