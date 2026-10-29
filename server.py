"""Web backend: serves the React app and runs the guidance pipeline on frames
streamed from the browser camera.

Browser (camera + speech) <-> WebSocket /ws <-> detector + tracker + instruction engine.
Browser high-resolution photo -> POST /api/read -> OCR + sign explanation.
"""

import asyncio
import threading
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

import config
from modules.detector import ObstacleDetector
from modules.guidance import GuidanceSession
from modules.ocr_reader import TextReader
from modules.sign_interpreter import SignInterpreter

state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    state["detector"] = ObstacleDetector()
    # Warm up so the first real frame is not slow
    state["detector"].detect(np.zeros((config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), np.uint8))
    state["ocr"] = TextReader()
    state["signs"] = SignInterpreter()
    # EasyOCR takes a few seconds to load; do it in the background
    threading.Thread(target=_warm_ocr, daemon=True).start()
    yield
    state.clear()


def _warm_ocr():
    try:
        state["ocr"].warm_up()
    except (RuntimeError, KeyError) as error:
        print(f"[OCR] {error}")


app = FastAPI(title="Actionable Guidance", lifespan=lifespan)


def decode(data: bytes):
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)


def process(frame, session: GuidanceSession) -> dict:
    result = session.step(frame)
    h, w = frame.shape[:2]
    return {
        "width": w,
        "height": h,
        "detections": [session.describe(d) for d in result["detections"]],
        "instruction": result["instruction"],
        "emergency": result["emergency"],
        "latency_ms": result["latency_ms"],
    }


def read_sign(frame) -> dict:
    """OCR on the full-resolution photo plus shape-based signs from the detector."""
    ocr = state["ocr"].read_scene(frame)
    h, w = frame.shape[:2]
    scale = config.FRAME_WIDTH / max(h, w)
    small = cv2.resize(frame, (int(w * scale), int(h * scale))) if scale < 1 else frame
    detections = state["detector"].detect(small, include_structure=False)
    for d in detections:
        # Back to full-resolution coordinates for the traffic light color check
        d["bbox"] = [int(v / min(scale, 1.0)) for v in d["bbox"]]
    return state["signs"].explain(ocr, detections, frame)


@app.get("/api/health")
def health():
    detector = state["detector"]
    return {
        "status": "ok",
        "model": config.MODEL_NAME,
        "structure_model": detector.has_structure,
        "device": detector.device,
    }


@app.websocket("/ws")
async def ws_guidance(ws: WebSocket):
    """Client sends one JPEG per message and waits for the JSON reply before
    sending the next, so frames never queue up (lowest latency)."""
    await ws.accept()
    session = GuidanceSession(state["detector"])  # per-connection tracking and throttle state
    try:
        while True:
            data = await ws.receive_bytes()
            frame = decode(data)
            if frame is None:
                await ws.send_json({"error": "bad frame"})
                continue
            result = await asyncio.to_thread(process, frame, session)
            await ws.send_json(result)
    except WebSocketDisconnect:
        pass


@app.post("/api/read")
async def read(image: UploadFile = File(...)):
    frame = decode(await image.read())
    if frame is None:
        return {"summary": "", "text": "", "error": "bad image"}
    try:
        return await asyncio.to_thread(read_sign, frame)
    except RuntimeError as error:
        return {"summary": "", "text": "", "error": str(error)}


@app.post("/api/ocr")
async def ocr(image: UploadFile = File(...)):
    """Plain text only; kept for older clients. New clients use /api/read."""
    result = await read(image)
    return {"text": result.get("text", ""), **({"error": result["error"]} if "error" in result else {})}


@app.get("/")
def index():
    page = config.FRONTEND_DIST / "index.html"
    if not page.exists():
        return HTMLResponse(
            "<h1>Frontend not built</h1><p>Run <code>cd frontend && npm install && npm run build</code>, "
            "then restart the server.</p>", status_code=503)
    return FileResponse(page)


if (config.FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=config.FRONTEND_DIST / "assets"), name="assets")


@app.get("/{name}")
def public_file(name: str):
    """Top-level files from the build (manifest, icons)."""
    path = (config.FRONTEND_DIST / name).resolve()
    if path.parent == config.FRONTEND_DIST.resolve() and path.is_file():
        return FileResponse(path)
    return index()
