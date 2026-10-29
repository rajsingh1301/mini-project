# Guide Eye: Real-Time Actionable Guidance for the Visually Impaired

An offline assistive prototype. A phone (or laptop) camera feeds a small
detection pipeline on a laptop, and the user hears short, prioritized
instructions such as *"Stop! stairs ahead"*, *"Door on your left"* or
*"Person approaching from your right"*. In **Read mode** the user points the
phone at a board or sign and hears what it says and what it means:
*"Exit sign. It says: EXIT. It shows the way out."*

No cloud APIs: all models run locally.

---

## Features

**Walk mode (obstacle guidance)**
1. **Obstacles:** YOLOv8 nano (COCO): people, vehicles, bicycles, chairs, tables, benches and more.
2. **Doors and stairs:** a YOLO11 nano model fine-tuned on Open Images V7 door/stairs labels (`models/door_stairs.pt`). Test-set accuracy is listed below.
3. **Stairs going up or down** (optional): a small classifier looks at each staircase and the app says *"Stop! stairs going down ahead"*. It needs a model trained from your own clips (see [Stairs direction](#stairs-direction)); until then, or whenever it is unsure, the app says plain *"Stairs ahead"*.
4. **Left / ahead / right zones** and **proximity** (immediate, near, far). For stairs, proximity comes from how low the staircase reaches in the frame, because a staircase looks large even far away.
5. **Tracking:** an object must be seen in 2 frames before it is announced (fewer false alarms), and a box that grows quickly is announced as *approaching* (d(area)/dt).
6. **Hazard Risk Index (HRI)** ranks everything in view, and only the most important thing is spoken. Stairs carry the highest class weight, stairs going down even more.
7. **No chatter:** repeat cooldowns, a global gap between phrases, and a one-time *"Path clear"* after a warning.

**Read mode (signs and boards)**
1. EasyOCR reads in natural order (lines top to bottom, words left to right). A contrast-enhanced second pass rescues faded or engraved text.
2. **Aiming help** for blind users: *"Text may be cut off. Move the phone right."*, *"The text is small. Move closer."*, *"The picture is blurry. Hold the phone steady."*, *"It is too dark."*
3. **Sign meaning:** exit, no entry, warning, push/pull, restroom, lift, stairs, platform, bus stop, entrance, open/closed, arrows, and **traffic light color** (*"Traffic light is red. Wait."*).
4. Reads continuously and only speaks again when the board changes.

**Phone app (React)**
- One big **Start** button, then two big buttons: **Read sign** and **Stop**. Plus Repeat and Mute.
- Everything important is spoken. Vibration on Stop and stairs warnings (Android). The screen stays on while walking. Phone light toggle in Read mode (Android).
- High-contrast yellow/black design with large text. Keyboard shortcuts for the laptop demo.

---

## Quick start

### 1. Set up (first time only)

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
```

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd frontend; npm install; npm run build; cd ..
```
If PowerShell blocks the script, run `Set-ExecutionPolicy -Scope Process Bypass` first.
Node.js 18+ is needed only to build the frontend.

### 2a. Use it from a phone (recommended demo)
```bash
python run_server.py
```
Connect the phone to the **same Wi-Fi** as the laptop and open the `https://<laptop-ip>:8000`
address it prints. Phones only allow the camera on HTTPS pages, so the script makes a
self-signed certificate. The first time, the browser warns about it: choose
**Advanced → Proceed** (Chrome) or **Show details → visit this website** (Safari).
Tap **Start**, allow the camera, and hold the phone at chest height, camera facing forward.

### 2b. Use it in the laptop browser
```bash
python run_server.py --http
```
Open http://localhost:8000.

### 2c. Desktop OpenCV app (no browser)
```bash
python main.py
```
`r` reads the sign in view, `q` quits.

---

## Door/stairs model

The model in `models/door_stairs.pt` was built with:
```bash
python training/prepare_dataset.py   # downloads all ~17,000 Open Images photos with door/stairs boxes
python training/train.py             # fine-tunes YOLO11n at 640 px, prints test metrics
```
Training uses the Apple GPU (MPS) or a CUDA GPU when available. 800 training photos (half with
stairs) are moved into the validation split, because the official one has only 36 stairs photos.
The new model is installed only if it scores higher than the installed one on the test split.

Training at 640 px takes about 10 GB of memory and many hours on a 16 GB laptop. To keep the
laptop free, open [`training/colab_train.ipynb`](training/colab_train.ipynb) in
[Google Colab](https://colab.research.google.com) (File > Open notebook > GitHub), pick a T4 GPU and
run all cells. Progress is saved to Google Drive, so a disconnected session continues where it
stopped (`python training/train.py --resume`). The last cell downloads the new model; put it in `models/`.

Held-out test split (665 Open Images photos):

| Class  | Precision | Recall | mAP50 | mAP50-95 |
|--------|-----------|--------|-------|----------|
| door   | 0.598     | 0.458  | 0.504 | 0.321    |
| stairs | 0.504     | 0.562  | 0.567 | 0.324    |
| all    |           |        | 0.535 | 0.322    |

Open Images photos are general web pictures, not walking footage, so treat these numbers
as a starting point and check the model on your own corridors and staircases.

---

## Stairs direction

A second, tiny model (YOLO11n classifier) looks at the stairs box and says *up* or *down*.
Public datasets with this label are not freely available, so it is trained from your own clips.
Each clip is all one direction, so nothing has to be labelled by hand.

**1. Record clips.** Hold the phone at chest height, like in Walk mode, and walk slowly towards
the staircase from about 5 m away until you reach it. Record 3 to 5 clips per direction at each
staircase, in different light, from slightly different angles.
- *up*: walk to the bottom step of a staircase that goes up.
- *down*: walk to the top step of a staircase that goes down.
- Use at least 5 different staircases (more is better). Each staircase is one "place".

**2. Sort them** (any video format; photos also work):
```text
datasets/stairs_clips/library/up/clip1.mp4
datasets/stairs_clips/library/down/clip1.mp4
datasets/stairs_clips/hostel/up/...
```

**3. Train:**
```bash
python training/prepare_stairs_direction.py   # finds the stairs in each frame, saves the crops
python training/train_stairs_direction.py     # trains, tests on unseen staircases, installs
```
Whole staircases are held out for testing, so the score shows how it does on stairs it has never
seen. The model is installed to `models/stairs_direction.pt` only if test accuracy is at least
85% (`STAIRS_DIRECTION_MIN_ACCURACY`). In the app, a direction is spoken only when 3 or more recent
frames agree; otherwise the phrase stays *"Stairs ahead"*.

---

## Tests and benchmark
```bash
python -m unittest discover -s tests -p "test_[a-z]*.py" -k Test   # Python unit tests
cd frontend && npm test                                            # frontend logic tests
python tests/test_benchmark.py                                     # latency/FPS for the paper
```
The tests replace YOLO and EasyOCR with fakes, so they run in under a second.
`tests/test_camera.py` and `tests/test_tts.py` are manual hardware checks.

---

## Project structure

```text
mini_project/
├── config.py                 # All thresholds, weights, model paths, OCR settings
├── main.py                   # Desktop app (OpenCV window + pyttsx3)
├── server.py                 # FastAPI backend: /ws walk stream, /api/read, serves frontend/dist
├── run_server.py             # Starts the server with HTTPS for phones
├── modules/
│   ├── camera.py             # Webcam capture & FPS
│   ├── detector.py           # COCO + door/stairs YOLO models
│   ├── tracker.py            # Frame-to-frame matching, flicker filter, approach rate
│   ├── instruction.py        # Zones, proximity, HRI, phrases, throttling
│   ├── guidance.py           # Detector -> tracker -> instructions, one session per user
│   ├── ocr_reader.py         # Text reading, line order, aiming hints
│   ├── sign_interpreter.py   # Sign meaning rules, traffic light color
│   └── tts_engine.py         # Non-blocking speech queue (desktop)
├── frontend/                 # React + Vite phone app
├── training/                 # Dataset builders, training scripts, Colab notebook
├── models/door_stairs.pt     # Trained door/stairs model (+ stairs_direction.pt once trained)
├── tests/                    # Unit tests, benchmark, hardware checks
└── paper/                    # Research paper draft
```

---

## Limitations
- Distance is estimated from box size and position, not measured. There is no depth sensor.
- Stairs up/down needs a classifier trained on your own clips; it is not included yet.
- Spoken phrases are English. Hindi boards can be read by setting `OCR_LANGUAGES = ["en", "hi"]` in `config.py` (larger model, not yet tested).
- This is a research prototype. It has not been validated with blind users and must not replace a cane or guide dog.
