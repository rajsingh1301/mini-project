# Real-Time Actionable Guidance for the Visually Impaired

An edge-AI assistive prototype that converts live video stream into concise, prioritized spoken action instructions for blind and low-vision individuals.

---

## 🚀 Key Features (50% Prototype Implemented)
1. **Real-Time Obstacle Detection:** Uses YOLOv8 Nano for fast, offline object identification (people, vehicles, chairs, tables, doors, stairs).
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
├── main.py                   # Complete real-time pipeline (Camera -> YOLO -> HRI -> Speech)
├── requirements.txt          # Python dependencies
│
├── modules/
│   ├── camera.py             # Frame capture & FPS calculation
│   ├── detector.py           # YOLOv8 nano detection wrapper
│   ├── instruction.py        # Direction & Hazard Risk Index prioritization logic
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

## 🛠️ How to Run

### 1. Activate Environment
```bash
source .venv/bin/activate
```

### 2. Run the Prototype
```bash
python main.py
```
*(Press **'q'** in the video window to stop)*

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
The academic paper draft is saved in [paper/research_paper_draft.md](file:///Users/mayankraj/developer/mini_project/paper/research_paper_draft.md). It contains:
- Abstract & Introduction
- Related Work Matrix (comparing Be My AI, Seeing AI, Envision, DeepNAVI, DrishT)
- Methodology & Mathematical formulation of the Hazard Risk Index
- System Architecture diagram (Mermaid)
- Experimental Evaluation metrics (FPS, Latency, Usability)
