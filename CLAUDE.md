# CLAUDE.md

## Project Idea & Goal
"Real-Time Actionable Guidance for the Visually Impaired" (college mini project).
Turn a live camera feed into short spoken instructions ("Stop! person ahead", "chair on left"), not long scene descriptions. Target: obstacles, stairs, doors and text in one pipeline.
Constraints: low latency, runs on a laptop/Colab, no expensive hardware, offline (no cloud APIs).

## Architecture / Pipeline
Camera -> Detector (YOLOv8n) -> Instruction Generator (direction + proximity + HRI + throttling) -> TTS (threaded queue). Plus on-demand OCR (press `r`).
Two front ends share the same modules: the desktop OpenCV app (`main.py`) and a web app (`server.py` + `web/index.html`). In the web app the browser owns camera and speech; the backend only does detection, instructions and OCR.

Data flow in [main.py](main.py), per loop iteration:
1. `VideoStream.read()` returns a 640x480 BGR frame (falls back to a synthetic "no camera" frame; detection is skipped then).
2. `ObstacleDetector.detect(frame)` returns dicts: class_name, confidence, bbox, norm_cx, area_ratio.
3. `InstructionGenerator.generate_instruction(dets)`:
   - direction from `norm_cx` (left <0.35, ahead, right >0.65)
   - proximity from bbox `area_ratio` (immediate >=0.20, near >=0.08, else far). This is a proxy, not real depth.
   - Hazard Risk Index = `area*10*proximity_boost + alignment*0.8 + class_weight*0.5`
   - picks the top non-throttled hazard (cooldown 2.0s, or 0.8s for "immediate") and returns a phrase, or None
4. `TTSEngine.speak(text, priority)` puts it on a queue (maxsize 3). A worker thread uses pyttsx3, with `say` as the macOS fallback. A "stop" phrase clears the backlog.
5. `draw_hud` renders boxes (red/amber/green by proximity), sector lines, the action banner, FPS and ms in an OpenCV window.
6. Key `r`: `TextReader.read(frame)` (EasyOCR, lazy-loaded, CPU) runs synchronously and the text is spoken. Key `q` quits.

## Tech Stack
Python, FastAPI + uvicorn (WebSocket), vanilla JS frontend, OpenCV (`opencv-python`), Ultralytics YOLOv8n (`yolov8n.pt`, COCO weights), pyttsx3, EasyOCR, numpy. Dependencies are in [requirements.txt](requirements.txt). Tests use `unittest`.

## Folder Structure
- `config.py`: all thresholds, class weights, camera, TTS and OCR settings
- `main.py`: desktop entry point, main loop and HUD
- `server.py`: FastAPI backend (`/ws` frame stream, `POST /api/ocr`, `/api/health`, serves `web/`)
- `web/index.html`: single-file browser UI (camera, canvas boxes, banner, speechSynthesis, log)
- `modules/`: `camera.py`, `detector.py`, `instruction.py`, `ocr_reader.py`, `tts_engine.py`
- `tests/`: `test_instruction.py`, `test_benchmark.py`, `test_camera.py`, `test_tts.py`
- `paper/research_paper_draft.md`: IEEE-style paper draft
- `models/easyocr/`: local OCR model cache (git-ignored)

## How to Run
```bash
source .venv/bin/activate
pip install -r requirements.txt
python main.py                              # desktop demo; q = quit, r = read text
uvicorn server:app --port 8000              # web app at http://localhost:8000
python tests/test_benchmark.py              # latency/FPS numbers for the paper
python -m unittest tests/test_instruction.py
python tests/test_camera.py                 # standalone camera check
python tests/test_tts.py                    # standalone audio check
```
macOS asks for camera permission on first run.

## Coding Rules / Conventions (as seen in code)
- Every tunable value lives in `config.py`; modules do `import config`. Do not hardcode thresholds.
- One class per module, each with a module docstring. Type hints on newer code. Short imperative comments.
- Detections are plain dicts with the keys listed above.
- The TTS queue is deliberately tiny. Never block the vision loop on audio, and drop stale messages.
- Instructions are short and imperative. Far objects off to the side are not announced.
- Do not claim door/stairs detection: COCO weights have no such classes (the README says this too).
- Tests add the repo root to `sys.path` and are run as scripts.

## Current Status
**Done**
- Web app: FastAPI backend and browser UI (tested with a real image over WebSocket and OCR; browser camera path not yet tested by me)
- Camera capture with FPS, YOLOv8n detection, left/ahead/right zoning
- Proximity levels, HRI ranking, speech throttling
- Non-blocking TTS, HUD
- On-demand OCR with the `r` key
- Benchmark script and paper draft

**In progress**
- OCR (`modules/ocr_reader.py`) is untracked in git. Several files also have uncommitted edits (README, config, main, tts_engine, requirements, .gitignore).
- Paper draft: it makes claims that are not yet verified (see Unknown).

**Todo / missing**
- Door and stairs detection (needs custom-trained weights or a dataset). Phrases like "step down" and "door on your left" are not produced anywhere in the code.
- Continuous OCR (currently on demand only)
- Real distance estimation (only a bbox-area proxy). The paper mentions the area derivative d(area)/dt, but the code does not use it.
- Tests for OCR, detector and TTS logic. Only `test_instruction.py` is a real unit test.
- Colab setup or notebook

**Unknown (ask the user)**
- Whether the paper's numbers (<150 ms latency, >25 FPS) are measured. Unconfirmed; check against `test_benchmark.py` output.
- Target platform for the final demo (Mac laptop vs Colab) and whether the stairs/door dataset or model exists.
- Final deliverables and deadline.
