"""Turns raw sign text and detections into a short spoken explanation.

OCR alone says *what* is written; this module says what the sign *means* for
someone walking ("Exit sign. It shows the way out."). Rules are offline and
deterministic, so the same board always gets the same explanation.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from modules import phrases


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

# The same sign kinds written in Hindi (Devanagari). No \b here: it breaks inside words that
# have vowel marks. Text and patterns are both NFC-normalized, so nukta forms match.
HINDI_PATTERNS = {
    "no_entry": r"प्रवेश\s*निषेध|प्रवेश\s*वर्जित|अंदर\s*आना\s*मना",
    "exit": r"निकास|बाहर\s*जाने\s*का\s*रास्ता",
    "warning": r"खतरा|ख़तरा|सावधान|चेतावनी|फिसलन",
    "bus_stop": r"बस\s*स्टॉप|बस\s*अड्डा",
    "stop": r"^\W*(रुकें|रुको|रुकिए)\W*$",
    "push": r"धक्का|धकेलें|ढकेलें",
    "pull": r"खींचें|खीचें",
    "restroom": r"शौचालय|प्रसाधन|टॉयलेट",
    "lift": r"लिफ़्ट|लिफ्ट",
    "stairs": r"सीढ",
    "escalator": r"एस्केलेटर|एस्कलेटर",
    "platform": r"प्लेटफ़?ॉर्म\s*(नंबर|नं\.?)?\s*[\d०-९]+",
    "prohibition": r"धूम्रपान\s*(निषेध|वर्जित|मना)|पार्किंग\s*(निषेध|मना)|हॉर्न\s*मना",
    "entrance": r"प्रवेश|अंदर\s*आइए",
    "open": r"^\s*खुला(\s*है)?\s*$",
    "closed": r"^\s*बंद(\s*है)?\s*$",
}


def hindi_form(text: str) -> str:
    """NFC text without the vowel sign ि. OCR often puts it on the wrong consonant
    ("नकिास" for "निकास"), so both the board text and the patterns are compared without it."""
    return unicodedata.normalize("NFC", text).replace("\u093f", "")


HINDI_PATTERNS = {k: hindi_form(v) for k, v in HINDI_PATTERNS.items()}

ARROWS = {"→": "right", "->": "right", "←": "left", "<-": "left", "↑": "straight ahead", "↓": "down"}


class SignInterpreter:
    def classify(self, text: str) -> Optional[Dict[str, str]]:
        """Returns the first matching sign rule, or None for ordinary text."""
        upper = text.upper()
        hindi = hindi_form(text)
        for kind, label, meaning, pattern in SIGN_RULES:
            if re.search(pattern, upper) or (kind in HINDI_PATTERNS and re.search(HINDI_PATTERNS[kind], hindi)):
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
                frame=None, lang: str = phrases.DEFAULT_LANGUAGE) -> Dict[str, Any]:
        """Builds the spoken summary for one Read request, in the app language.

        The board's own text is read out as written; only our words are translated.
        """
        lang = phrases.normalize(lang)
        r = phrases.read_text(lang)
        text = ocr.get("text", "")
        parts: List[str] = []
        kind = None

        # Signs the detector recognizes by shape, even without readable text
        for det in detections or []:
            name = det["class_name"]
            if name == "traffic light" and frame is not None:
                color = self.traffic_light_color(frame, det["bbox"])
                if color:
                    parts.append(r["traffic_light"].format(color=r["colors"][color], advice=r["advice"][color]))
                else:
                    parts.append(r["traffic_light_unknown"])
                kind = kind or "traffic_light"
            elif name == "stop sign" and "stop" not in (kind or ""):
                parts.append(r["stop_sign"])
                kind = "stop"

        rule = self.classify(text) if text else None
        if rule and rule["kind"] != kind:
            # Skip the label when the detector already announced the same sign
            label, meaning = phrases.sign_text(lang, rule["kind"], rule["label"], rule["meaning"])
            parts.append(r["sign_label"].format(label=label))
        if rule:
            kind = rule["kind"]
            label, meaning = phrases.sign_text(lang, kind, rule["label"], rule["meaning"])
        if text:
            parts.append(r["says"].format(text=text))
            arrow = self.arrow_direction(text)
            if arrow:
                parts.append(r["arrow"][arrow])
        if rule and meaning:
            parts.append(meaning)

        # Hints come as language-independent codes from TextReader; plain strings
        # (older callers, tests) are used as given.
        codes = ocr.get("hint_codes")
        hints = [phrases.aiming_hint(lang, code, args) for code, args in codes] if codes else ocr.get("hints", [])
        if not parts:
            parts.append(r["no_text"])
            parts.extend(hints[:1])
        elif hints:
            parts.append(hints[0])

        return {"kind": kind, "summary": " ".join(parts), "text": text,
                "lines": ocr.get("lines", []), "hints": hints}
