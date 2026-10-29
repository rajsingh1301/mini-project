# CLAUDE.md

## Project Idea & Goal
"Real-Time Actionable Guidance for the Visually Impaired" (college mini project, app name "Guide Eye").
Turn a live camera feed into short spoken instructions ("Stop! stairs ahead", "Chair on your left"), not long scene descriptions, and read/explain signs and boards on request. Target: obstacles, stairs, doors and text in one pipeline.
Constraints: low latency, runs on a laptop (phone is the camera + speaker via the web app), no expensive hardware, offline (no cloud APIs).

## Architecture / Pipeline
Camera -> `ObstacleDetector` (COCO YOLOv8n + custom door/stairs YOLO11n) -> `ObjectTracker` (IoU matching, hits, d(area)/dt) -> `InstructionGenerator` (direction + proximity + HRI + throttling) -> speech.
Read path: high-res photo -> `TextReader.read_scene` (EasyOCR, line ordering, CLAHE retry, aiming hints) -> `SignInterpreter.explain` (sign rules, traffic light color) -> speech.
`GuidanceSession` (modules/guidance.py) wires detector -> tracker -> instructions; one per desktop app or per WebSocket client. The detector is shared (thread lock inside).

Two front ends share the modules:
- Desktop OpenCV app `main.py` (pyttsx3 TTS queue, HUD, key `r` = read sign, `q` = quit).
- Web app: `server.py` (FastAPI) + `frontend/` (React + Vite). Browser owns camera, speech (speechSynthesis), vibration and wake lock. Walk mode streams 640px JPEGs over `/ws` (one in flight at a time); Read mode posts full-res photos to `/api/read` in a loop, waiting for speech to finish between reads.

Key rules in `InstructionGenerator`:
- direction from `norm_cx` (left <0.35, ahead, right >0.65)
- proximity from bbox `area_ratio` (immediate >=0.20, near >=0.08); for `FLOOR_CLASSES` (stairs) from `norm_bottom` instead. Proxy, not real depth.
- HRI = `area*10*proximity_boost + alignment*0.8 + class_weight*0.5 + approach*0.3`
- detections with `hits < CONFIRM_HITS` are ignored (flicker filter); `growth_rate >= APPROACH_RATE` -> "approaching"
- throttling: same class+direction 4.0s (`AUDIO_THROTTLE_SECONDS`/`CRITICAL_OVERRIDE_SECONDS`), far 8.0s, 2.0s global gap for non-immediate; "Path clear" once after an ahead warning
- a phrase starting with "Stop" is an emergency (interrupts speech, vibrates)

## Tech Stack
Python 3.13, Ultralytics (YOLOv8n COCO + YOLO11n fine-tuned), EasyOCR, OpenCV, FastAPI + uvicorn, pyttsx3, numpy, cryptography (self-signed cert). Frontend: React 18 + Vite 5, plain JS, no UI library. Tests: `unittest` (Python), `node --test` (frontend pure helpers).

## Folder Structure
- `config.py`: all thresholds, class weights, model paths, tracker, TTS and OCR settings
- `main.py`: desktop entry point, main loop and HUD
- `server.py`: FastAPI (`/ws`, `POST /api/read`, `POST /api/ocr` legacy, `/api/health`, serves `frontend/dist`)
- `run_server.py`: starts the server; HTTPS with an auto-made self-signed cert so phones get camera access (`--http` for localhost only)
- `modules/`: `camera.py`, `detector.py`, `tracker.py`, `instruction.py`, `guidance.py`, `ocr_reader.py`, `sign_interpreter.py`, `tts_engine.py`
- `frontend/src/`: `App.jsx`, `hooks/` (camera, speech, settings, wake lock, guidance stream, sign reader), `components/`, `lib/guidance.js` (+ `.test.js`)
- `training/`: `prepare_dataset.py` (Open Images door/stairs -> YOLO format), `train.py` (fine-tune, install to `models/door_stairs.pt`, test metrics)
- `models/door_stairs.pt`: trained door/stairs weights (tracked). `models/easyocr/` is a git-ignored cache.
- `tests/`: unit tests `test_instruction`, `test_tracker`, `test_detector`, `test_ocr`, `test_tts_engine`, `test_server`; scripts `test_benchmark.py`, `test_camera.py`, `test_tts.py`
- `paper/research_paper_draft.md`: IEEE-style paper draft
- Git-ignored: `datasets/`, `runs/`, `certs/`, `frontend/node_modules`, `frontend/dist`

## How to Run
```bash
source .venv/bin/activate
pip install -r requirements.txt
(cd frontend && npm install && npm run build)   # once, and after frontend changes
python run_server.py                             # phone: https://<laptop-ip>:8000 (accept cert warning)
python run_server.py --http                      # laptop browser: http://localhost:8000
python main.py                                   # desktop demo; q = quit, r = read sign
python -m unittest discover -s tests -p "test_[a-z]*.py" -k Test   # all Python unit tests
(cd frontend && npm test)                        # frontend helper tests
python tests/test_benchmark.py                   # latency/FPS numbers for the paper
python training/prepare_dataset.py && python training/train.py      # rebuild door/stairs model
```
Frontend dev with hot reload: `uvicorn server:app --port 8000` + `cd frontend && npm run dev` (Vite proxies `/api` and `/ws`).

## Coding Rules / Conventions (as seen in code)
- Every tunable value lives in `config.py`; modules do `import config`. Do not hardcode thresholds.
- One class per module, each with a module docstring. Type hints on newer code. Short imperative comments.
- Detections are plain dicts: class_name, class_id, confidence, bbox, center_x/y, norm_cx, norm_bottom, area_ratio; the tracker adds track_id, hits, growth_rate.
- Never block the vision loop on audio; drop stale speech instead of queueing (desktop queue maxsize 3; browser drops non-urgent speech while speaking).
- Instructions are short and imperative. Far objects off to the side are not announced.
- Door/stairs come only from the trained model; report its measured test metrics, not more.
- Python tests add the repo root to `sys.path`, fake YOLO/EasyOCR, and also run as scripts.
- Frontend: hooks own side effects; pure logic goes in `lib/` with node tests. Big touch targets, high contrast, everything important is spoken.

## Current Status
**Done**
- Door/stairs detection: YOLO11n fine-tuned on Open Images V7 (5959 train / 234 val / 665 test images)
- Tracker with flicker filter and approach detection (d(area)/dt); floor-based proximity for stairs; "Path clear"
- Sign reading: line ordering, CLAHE retry, aiming hints (cut off / too small / blurry / dark), sign meaning rules, traffic light color
- React frontend (Walk + Read modes, repeat, mute, vibration, wake lock, torch, settings), HTTPS runner for phones
- Browser camera path verified end to end with headless Chrome and a fake camera clip (walk and read modes)
- Unit tests for instruction, tracker, detector, OCR, sign interpreter, TTS queue, server/WebSocket

**Todo / missing**
- Real-world validation with blind users and on a real phone walk (only tested with clips and photos)
- Stairs up vs down is not distinguished; distance is still a bbox proxy (no depth model)
- Hindi OCR/speech: possible via `OCR_LANGUAGES = ["en", "hi"]` but untested; instruction phrases are English only
- Colab notebook

**Unknown (ask the user)**
- Target platform for the final demo (phone + Mac laptop vs Colab)
- Final deliverables and deadline
