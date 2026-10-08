# Real-Time Actionable Guidance for the Visually Impaired

An edge-AI assistive prototype that converts live video stream into concise, prioritized spoken action instructions for blind and low-vision individuals.

---

## 🚀 Key Features
1. **Real-Time Obstacle Detection:** Uses YOLOv8 Nano for fast, local identification of COCO classes such as people, vehicles, chairs, tables, bottles, backpacks, and suitcases.
2. **Horizontal Sector Zoning:** Divides camera field-of-view into `Left`, `Path (Ahead)`, and `Right` to give precise spatial context.
3. **Hazard Risk Index (HRI):** Mathematically ranks obstacles using:
   - Proximity via bounding box area scale ($\text{area}_{box} / \text{area}_{frame}$)
   - Collision trajectory alignment ($1 - 2 \cdot |x_{norm} - 0.5|$)
   - Class severity weighting
4. **Action-Oriented Spoken Guidance:** Speaks immediate verbs (e.g. *"Stop! Person ahead"*, *"Chair on left"*), avoiding wordy passive descriptions.
5. **Zero-Lag Asynchronous TTS:** Non-blocking threaded audio queue with chatter suppression (prevents repetitive loop speaking).
6. **Live Visual HUD:** Visualizes real-time FPS, latency in milliseconds, bounding box proximity color codes (Green = Safe, Amber = Near, Red = Immediate Hazard).

---

## 📁 Project Structure

```text
mini_project/
│
├── config.py                 # System thresholds, camera size, HRI weights, TTS rate
├── main.py                   # Desktop real-time pipeline (Camera -> YOLO -> HRI -> Speech)
├── server.py                 # FastAPI backend for the web app
├── web/index.html            # Browser UI (camera, boxes, banner, speech)
├── requirements.txt          # Python dependencies
│
├── modules/
│   ├── camera.py             # Frame capture & FPS calculation
│   ├── detector.py           # YOLOv8 nano detection wrapper
│   ├── instruction.py        # Direction & Hazard Risk Index prioritization logic
│   ├── ocr_reader.py         # On-demand text reading (EasyOCR)
│   └── tts_engine.py         # Non-blocking threaded speech synthesizer
│
├── paper/
│   └── research_paper_draft.md # Academic research paper formatted in IEEE/ACM style
│
└── tests/
    ├── test_instruction.py   # Unit test for spatial sectors & priority rules
    ├── test_benchmark.py     # Latency & FPS benchmark for paper evaluation
    ├── test_camera.py        # Standalone webcam test
    └── test_tts.py           # Standalone audio speech test
```

---

## 🛠️ Presentation quick start

### 1. Set up the environment (first time only)

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (CMD)**
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
If PowerShell blocks the script, run `Set-ExecutionPolicy -Scope Process Bypass` first.
On later runs, only the activate line is needed. Use `python3` instead of `python`
on macOS/Linux if `python` is not found.

### 2. Run the Prototype
```bash
python main.py
```
*(Press **'q'** in the video window to stop)*

Before presenting, allow camera access when macOS or Windows asks (on Windows: Settings > Privacy > Camera). Keep a chair or a
person in the centre of the camera view for a repeatable demo. A small object
near either edge demonstrates the left/right cue; a large centre object should
produce the red **Stop** cue.

## Current scope and next upgrade

The included `yolov8n.pt` model was trained on COCO. COCO has no `door` or
`stairs` class, so this version must be presented as a **general obstacle
guidance prototype**, not as validated stair or door detection. The action
pipeline, direction logic, priority ranking, HUD, and offline speech are fully
implemented. The next milestone is to plug in a custom model trained with
door/stair labels, then add OCR on sampled frames.

## Reading a sign or label

Point the camera at clear, well-lit English text and press **`r`** in the video
window. The system pauses only for that OCR request, shows `Text: ...` in the
HUD, and reads the result aloud. This on-demand design avoids slowing the live
obstacle loop. The first OCR request may take longer while EasyOCR loads its
recognition model.

EasyOCR stores its downloaded model files locally in `models/easyocr/` inside
this project, so the text-reading demo also works after the initial download.

### 2b. Run the Web App (frontend + backend)
```bash
uvicorn server:app --port 8000
```
Open http://localhost:8000, press **Start**, allow the camera. The browser sends
frames to the FastAPI backend over a WebSocket (`/ws`), draws the returned boxes,
shows the action banner and speaks instructions with the browser's speech
synthesis. **Read text** calls `POST /api/ocr`. Camera access needs `localhost`
or HTTPS.

### 3. Run Benchmark (To get numbers for your Research Paper)
```bash
python tests/test_benchmark.py
```

### 4. Run Unit Tests
```bash
python -m unittest tests/test_instruction.py
```

---

## 📄 Research Paper
The academic paper draft is saved in [paper/research_paper_draft.md](paper/research_paper_draft.md). It contains:
- Abstract & Introduction
- Related Work Matrix (comparing Be My AI, Seeing AI, Envision, DeepNAVI, DrishT)
- Methodology & Mathematical formulation of the Hazard Risk Index
- System Architecture diagram (Mermaid)
- Experimental Evaluation metrics (FPS, Latency, Usability)
