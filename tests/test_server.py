"""End-to-end tests of the web backend and guidance session with fake models.

Covers the WebSocket frame loop, tracking confirmation, the /api/read sign
explanation and the health endpoint, without loading YOLO or EasyOCR.
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import server
from modules.detector import make_detection
from modules.guidance import GuidanceSession


class FakeDetector:
    """A person filling the center of every frame, plus stairs from the structure model."""
    device = "cpu"
    has_structure = True

    def __init__(self):
        self.structure_calls = 0

    def detect(self, frame, include_structure=True):
        h, w = frame.shape[:2]
        dets = [make_detection("person", 0, 0.9, [w * 0.25, 0, w * 0.75, h], w, h)]
        if include_structure:
            dets += self.detect_structure(frame)
        return dets

    def detect_structure(self, frame):
        self.structure_calls += 1
        h, w = frame.shape[:2]
        return [make_detection("stairs", 1, 0.8, [0, h * 0.5, w * 0.3, h * 0.7], w, h)]


class FakeReader:
    def warm_up(self):
        pass

    def read_scene(self, frame):
        return {"text": "EXIT", "lines": ["EXIT"], "confidence": 0.9, "quality": {}, "hints": []}


def jpeg(w=640, h=480):
    ok, buf = cv2.imencode(".jpg", np.full((h, w, 3), 127, np.uint8))
    return buf.tobytes()


class TestGuidanceSession(unittest.TestCase):
    def test_confirmation_and_structure_cadence(self):
        detector = FakeDetector()
        session = GuidanceSession(detector)
        frame = np.zeros((480, 640, 3), np.uint8)
        first = session.step(frame, now=100.0)
        # One sighting is not enough to speak
        self.assertIsNone(first["instruction"])
        second = session.step(frame, now=100.1)
        self.assertEqual(second["instruction"], "Stop! person ahead")
        self.assertTrue(second["emergency"])
        # Structure model ran on frame 0 only; frame 1 reused its boxes
        self.assertEqual(detector.structure_calls, 1)
        self.assertIn("stairs", [d["class_name"] for d in second["detections"]])

    def test_describe(self):
        session = GuidanceSession(FakeDetector())
        out = session.step(np.zeros((480, 640, 3), np.uint8), now=1.0)
        described = [session.describe(d) for d in out["detections"]]
        person = next(d for d in described if d["label"] == "person")
        self.assertEqual((person["direction"], person["proximity"], person["approaching"]), ("ahead", "immediate", False))


class TestServer(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        patches = [mock.patch.object(server, "ObstacleDetector", FakeDetector),
                   mock.patch.object(server, "TextReader", FakeReader)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.client = TestClient(server.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def test_health(self):
        body = self.client.get("/api/health").json()
        self.assertEqual(body["status"], "ok")
        self.assertTrue(body["structure_model"])

    def test_websocket_stream(self):
        with self.client.websocket_connect("/ws") as ws:
            replies = []
            for _ in range(3):
                ws.send_bytes(jpeg())
                replies.append(ws.receive_json())
        self.assertEqual(replies[0]["width"], 640)
        labels = {d["label"] for d in replies[1]["detections"]}
        self.assertEqual(labels, {"person", "stairs"})
        self.assertIn("Stop! person ahead", [r["instruction"] for r in replies])

    def test_bad_frame(self):
        with self.client.websocket_connect("/ws") as ws:
            ws.send_bytes(b"not a jpeg")
            self.assertEqual(ws.receive_json(), {"error": "bad frame"})

    def test_read_explains_sign(self):
        body = self.client.post("/api/read", files={"image": ("f.jpg", jpeg(1920, 1080), "image/jpeg")}).json()
        self.assertEqual(body["kind"], "exit")
        self.assertTrue(body["summary"].startswith("Exit sign. It says: EXIT."))

    def test_ocr_alias(self):
        body = self.client.post("/api/ocr", files={"image": ("f.jpg", jpeg(), "image/jpeg")}).json()
        self.assertEqual(body, {"text": "EXIT"})

    def test_index_served_or_explained(self):
        response = self.client.get("/")
        if (config.FRONTEND_DIST / "index.html").exists():
            self.assertEqual(response.status_code, 200)
            self.assertIn("<div id=\"root\">", response.text)
        else:
            self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
