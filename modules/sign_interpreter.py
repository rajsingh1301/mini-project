"""Turns raw sign text and detections into a short spoken explanation.

OCR alone says *what* is written; this module says what the sign *means* for
someone walking ("Exit sign. It shows the way out."). Rules are offline and
deterministic, so the same board always gets the same explanation.
"""

import re
from typing import Any, Dict, List, Optional

import cv2
import numpy as np


# (kind, spoken label, meaning, regex on upper-cased text). First match wins,
# so more specific rules come before general ones.
SIGN_RULES = [
    ("no_entry", "No entry sign", "Do not go this way.",
     r"\b(NO ENTRY|DO NOT ENTER|NO ENTRANCE|ENTRY PROHIBITED|NO ADMISSION|STAFF ONLY|AUTHORI[SZ]ED PERSONNEL ONLY)\b"),
    ("exit", "Exit sign", "It shows the way out.",
     r"\b(EXIT|WAY OUT|FIRE EXIT|EMERGENCY EXIT)\b"),
    ("warning", "Warning sign", "Be careful here.",
     r"\b(DANGER|WARNING|CAUTION|HIGH VOLTAGE|WET FLOOR|SLIPPERY|MIND THE (STEP|GAP|HEAD)|WATCH YOUR STEP|CONSTRUCTION|HAZARD)\b"),
    ("bus_stop", "Bus stop sign", "Buses stop here.", r"\bBUS\s*STOP\b"),
    ("stop", "Stop sign", "Stop here before going on.", r"^\W*STOP\W*$"),
    ("push", "Door sign", "Push the door to open it.", r"\bPUSH\b"),
    ("pull", "Door sign", "Pull the door to open it.", r"\bPULL\b"),
    ("restroom", "Restroom sign", "Toilets are this way.",
     r"\b(TOILETS?|RESTROOMS?|WASHROOMS?|W\.?C|LADIES|GENTS|LAVATORY)\b"),
    ("lift", "Lift sign", "A lift is nearby.", r"\b(LIFTS?|ELEVATORS?)\b"),
    ("stairs", "Stairs sign", "Stairs are nearby. Take care.", r"\b(STAIRS?|STAIRCASE|STAIRWAY|STEPS)\b"),
    ("escalator", "Escalator sign", "An escalator is nearby.", r"\bESCALATORS?\b"),
    ("platform", "Platform sign", "", r"\bPLATFORM\s*(NO\.?)?\s*\d+\b"),
    ("prohibition", "Prohibition sign", "", r"\bNO (SMOKING|PARKING|PHOTOGRAPHY|FOOD|HORN|ENTRY)\b"),
    ("entrance", "Entrance sign", "This is the way in.", r"\b(ENTRANCE|ENTRY|WAY IN)\b"),
    ("open", "Open sign", "It is open now.", r"^\s*(WE ARE )?OPEN\s*$"),
    ("closed", "Closed sign", "It is closed now.", r"^\s*(SORRY,? (WE ARE )?)?CLOSED\s*$"),
]

ARROWS = {"→": "right", "->": "right", "←": "left", "<-": "left", "↑": "straight ahead", "↓": "down"}


class SignInterpreter:
    def classify(self, text: str) -> Optional[Dict[str, str]]:
        """Returns the first matching sign rule, or None for ordinary text."""
        upper = text.upper()
        for kind, label, meaning, pattern in SIGN_RULES:
            if re.search(pattern, upper):
                return {"kind": kind, "label": label, "meaning": meaning}
        return None

    @staticmethod
    def arrow_direction(text: str) -> Optional[str]:
        for symbol, direction in ARROWS.items():
            if symbol in text:
                return direction
        return None

    @staticmethod
    def traffic_light_color(frame, bbox: List[int]) -> Optional[str]:
        """Dominant lit color inside a traffic light box: red, yellow or green."""
        x1, y1, x2, y2 = bbox
        crop = frame[max(0, y1):y2, max(0, x1):x2]
        if crop.size == 0:
            return None
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        # Only bright, saturated pixels belong to the lit lamp
        lit = (hsv[..., 1] > 100) & (hsv[..., 2] > 150)
        hue = hsv[..., 0]
        counts = {
            "red": int(np.count_nonzero(lit & ((hue < 10) | (hue > 160)))),
            "yellow": int(np.count_nonzero(lit & (hue >= 15) & (hue <= 35))),
            "green": int(np.count_nonzero(lit & (hue >= 40) & (hue <= 95))),
        }
        color, n = max(counts.items(), key=lambda kv: kv[1])
        return color if n >= max(4, 0.02 * crop.shape[0] * crop.shape[1]) else None

    def explain(self, ocr: Dict[str, Any], detections: Optional[List[Dict[str, Any]]] = None,
                frame=None) -> Dict[str, Any]:
        """Builds the spoken summary for one Read request."""
        text = ocr.get("text", "")
        parts: List[str] = []
        kind = None

        # Signs the detector recognizes by shape, even without readable text
        for det in detections or []:
            name = det["class_name"]
            if name == "traffic light" and frame is not None:
                color = self.traffic_light_color(frame, det["bbox"])
                advice = {"red": "Wait.", "green": "It is safe to cross if the road is clear.",
                          "yellow": "It is about to change. Wait."}
                if color:
                    parts.append(f"Traffic light is {color}. {advice[color]}")
                else:
                    parts.append("There is a traffic light.")
                kind = kind or "traffic_light"
            elif name == "stop sign" and "stop" not in (kind or ""):
                parts.append("There is a stop sign.")
                kind = "stop"

        rule = self.classify(text) if text else None
        if rule and rule["kind"] != kind:
            # Skip the label when the detector already announced the same sign
            parts.append(f"{rule['label']}.")
        if rule:
            kind = rule["kind"]
        if text:
            parts.append(f"It says: {text}.")
            arrow = self.arrow_direction(text)
            if arrow:
                parts.append(f"The arrow points {arrow}.")
        if rule and rule["meaning"]:
            parts.append(rule["meaning"])

        hints = ocr.get("hints", [])
        if not parts:
            parts.append("No text found.")
            parts.extend(hints[:1])
        elif hints:
            parts.append(hints[0])

        return {"kind": kind, "summary": " ".join(parts), "text": text,
                "lines": ocr.get("lines", []), "hints": hints}
