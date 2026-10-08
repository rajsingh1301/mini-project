"""Non-blocking, low-latency Text-to-Speech (TTS) audio engine.
"""

import queue
import threading
import time
import subprocess
import platform
import config

try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False


class TTSEngine:
    def __init__(self, rate: int = config.TTS_RATE, volume: float = config.TTS_VOLUME):
        self.rate = rate
        self.volume = volume
        self.msg_queue = queue.Queue(maxsize=3) # Keep queue tiny to prevent audio lag backlog
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.is_speaking = False
        self.worker_thread.start()

    def _worker_loop(self):
        engine = None
        if HAS_PYTTSX3:
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", self.rate)
                engine.setProperty("volume", self.volume)
            except Exception as e:
                print(f"[TTS Warning] pyttsx3 init error: {e}. Falling back to native system voice.")
                engine = None

        while self.running:
            try:
                text = self.msg_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            self.is_speaking = True
            try:
                if engine is not None:
                    engine.say(text)
                    engine.runAndWait()
                elif platform.system() == "Darwin":
                    # Instant native macOS speech fallback
                    subprocess.run(["say", "-r", str(self.rate), text], check=False)
                else:
                    # Linux/Windows console fallback
                    print(f"[AUDIO OUT]: {text}")
            except Exception as e:
                print(f"[TTS Error] {e}")
            finally:
                self.is_speaking = False
                self.msg_queue.task_done()

    def speak(self, text: str, priority: bool = False):
        """Dispatches an instruction to the speech queue.
        If priority is True and queue is full, clears backlog to speak immediately.
        """
        if not text:
            return

        if priority and not self.msg_queue.empty():
            # Clear stale messages
            try:
                while not self.msg_queue.empty():
                    self.msg_queue.get_nowait()
                    self.msg_queue.task_done()
            except Exception:
                pass

        try:
            self.msg_queue.put_nowait(text)
        except queue.Full:
            # Drop older message and insert new one
            try:
                self.msg_queue.get_nowait()
                self.msg_queue.task_done()
            except queue.Empty:
                pass
            try:
                self.msg_queue.put_nowait(text)
            except queue.Full:
                # A concurrent producer may have filled the tiny queue.
                # Do not block the vision loop for stale audio.
                pass

    def stop(self):
        self.running = False
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)
