"""Checks that the pipeline works with no internet (run it as a script, not a unit test).

Network access is blocked inside this process, then every component runs for real:
object detector, door/stairs model, OCR (English, and Hindi if its model is cached),
phrases and the desktop speech engine. A component that tries to download or call
out fails here instead of on a phone with no signal.

    python tests/check_offline.py
"""

import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class NetworkBlocked(OSError):
    pass


def block_network():
    def refuse(*args, **kwargs):
        raise NetworkBlocked("network access attempted")
    # Local connections (e.g. multiprocessing helpers) stay allowed
    real_connect = socket.socket.connect

    def connect(self, address, *a, **k):
        if isinstance(address, tuple) and address and address[0] not in ("127.0.0.1", "localhost", "::1"):
            refuse()
        return real_connect(self, address, *a, **k)

    socket.socket.connect = connect
    socket.getaddrinfo = refuse
    socket.create_connection = refuse


def main() -> int:
    import cv2
    import numpy as np

    import config
    from modules import phrases

    results = []

    def check(name, fn):
        try:
            detail = fn()
            results.append((name, True, detail or ""))
        except Exception as error:  # Any failure, including NetworkBlocked, is a result
            results.append((name, False, f"{type(error).__name__}: {error}"))

    # Make the test images before blocking, so nothing below needs the network
    frame = np.full((480, 640, 3), 120, np.uint8)
    sign = np.full((600, 1000, 3), 255, np.uint8)
    cv2.putText(sign, "EXIT", (250, 380), cv2.FONT_HERSHEY_SIMPLEX, 6, (0, 0, 0), 14)

    block_network()
    check("network is blocked", lambda: (_ for _ in ()).throw(AssertionError("still reachable"))
          if _reachable() else "outside connections refused")

    from modules.detector import ObstacleDetector
    detector = {}

    def load_detector():
        detector["d"] = ObstacleDetector()
        detector["d"].detect(frame)
        return f"COCO model + door/stairs model ({'present' if detector['d'].has_structure else 'MISSING'})"
    check("object detector", load_detector)
    check("door/stairs model installed", lambda: None if config.STRUCTURE_MODEL.exists()
          else (_ for _ in ()).throw(FileNotFoundError(f"{config.STRUCTURE_MODEL} (run training/train.py)")))

    from modules.ocr_reader import TextReader
    from modules.sign_interpreter import SignInterpreter
    reader = TextReader()

    def read_english():
        out = reader.read_scene(sign, "en")
        summary = SignInterpreter().explain(out, lang="en")["summary"]
        assert "EXIT" in out["text"].upper(), f"read {out['text']!r}"
        return summary
    check("OCR English", read_english)

    def read_hindi():
        cached = {p.name for p in config.OCR_MODEL_DIR.glob("*.pth")}
        if not any("devanagari" in name for name in cached):
            return "SKIPPED: Hindi model not downloaded yet (first Hindi read needs internet once)"
        reader.read_scene(sign, "hi")
        return "Hindi model loads from disk"
    check("OCR Hindi", read_hindi)

    def speak_phrases():
        for lang in phrases.LANGUAGES:
            assert phrases.instruction(lang, "person", "ahead", "immediate")
        return "English and Hindi phrases are built in code, no translation service"
    check("phrases", speak_phrases)

    def desktop_voice():
        import platform
        import shutil
        if platform.system() == "Darwin":
            assert shutil.which("say"), "macOS `say` not found"
            return "macOS system voices"
        import pyttsx3
        pyttsx3.init()
        return "pyttsx3 system voices"
    check("desktop speech", desktop_voice)

    width = max(len(name) for name, *_ in results)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name:{width}s}  {detail}")
    print("\nThe phone app speaks with the phone's own voices; prefer voices marked as installed "
          "on the device (the app picks those first). Online-only voices need a connection.")
    return 0 if all(ok for _, ok, _ in results) else 1


def _reachable() -> bool:
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=2)
        return True
    except NetworkBlocked:
        return False
    except OSError:
        return False


if __name__ == "__main__":
    sys.exit(main())
