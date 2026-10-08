"""Web backend: serves the browser UI and runs the guidance pipeline on frames
streamed from the browser camera.

Browser (camera + speech) <-> WebSocket /ws <-> detector + instruction engine.
"""

import asyncio
import time
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import config
from modules.detector import ObstacleDetector
from modules.instruction import InstructionGenerator
from modules.ocr_reader import TextReader

state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    state["detector"] = ObstacleDetector()
    # Warm up so the first real frame is not slow
    state["detector"].detect(np.zeros((config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), np.uint8))
    state["ocr"] = TextReader()
    yield
    state.clear()


app = FastAPI(title="Actionable Guidance", lifespan=lifespan)


def decode(data: bytes):
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)


def process(frame, engine: InstructionGenerator) -> dict:
    t0 = time.time()
    detections = state["detector"].detect(frame)
    instruction = engine.generate_instruction(detections)
    h, w = frame.shape[:2]
    return {
        "width": w,
        "height": h,
        "detections": [
            {
                "label": d["class_name"],
                "confidence": d["confidence"],
                "bbox": d["bbox"],
                "proximity": engine.determine_proximity(d["area_ratio"]),
                "direction": engine.determine_direction(d["norm_cx"]),
            }
            for d in detections
        ],
        "instruction": instruction,
        "emergency": bool(instruction and "stop" in instruction.lower()),
        "latency_ms": round((time.time() - t0) * 1000, 1),
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "model": config.MODEL_NAME}


@app.websocket("/ws")
async def ws_guidance(ws: WebSocket):
    """Client sends one JPEG per message and waits for the JSON reply before
    sending the next, so frames never queue up (lowest latency)."""
    await ws.accept()
    engine = InstructionGenerator()  # per-connection throttle state
    try:
        while True:
            data = await ws.receive_bytes()
            frame = decode(data)
            if frame is None:
                await ws.send_json({"error": "bad frame"})
                continue
            result = await asyncio.to_thread(process, frame, engine)
            await ws.send_json(result)
    except WebSocketDisconnect:
        pass


@app.post("/api/ocr")
async def ocr(image: UploadFile = File(...)):
    frame = decode(await image.read())
    if frame is None:
        return {"text": "", "error": "bad image"}
    try:
        text = await asyncio.to_thread(state["ocr"].read, frame)
    except RuntimeError as error:
        return {"text": "", "error": str(error)}
    return {"text": text}


@app.get("/")
def index():
    return FileResponse(config.BASE_DIR / "web" / "index.html")


app.mount("/static", StaticFiles(directory=config.BASE_DIR / "web"), name="static")
