# StorePulse AI — Application Entry Point
# Developer: Omkar Gurav

import time
import cv2
import asyncio
import sys
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.ws_manager import manager
from backend.pipeline import pipeline_runner
from backend.routers import zones, layouts, analytics as analytics_router


async def broadcast_worker():
    while True:
        payload = pipeline_runner.get_latest_metrics()
        if payload is not None:
            await manager.broadcast(payload)
            pipeline_runner.clear_latest_metrics()
        await asyncio.sleep(0.1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[StorePulse AI] Starting analytics pipeline...")
    pipeline_runner.start()
    task = asyncio.create_task(broadcast_worker())
    yield
    task.cancel()
    print("[StorePulse AI] Stopping analytics pipeline...")
    pipeline_runner.stop()


app = FastAPI(
    title="StorePulse AI — Retail Intelligence API",
    description=(
        "StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator. "
        "Developer: Omkar Gurav."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────
app.include_router(zones.router)
app.include_router(layouts.router)
app.include_router(analytics_router.router)


# ── WebSocket ─────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ── MJPEG stream ──────────────────────────────────────────────────────
def frame_generator():
    """Generator that yields JPEG frames for MJPEG streaming."""
    while True:
        frame = pipeline_runner.get_latest_snapshot()
        if frame is None:
            time.sleep(0.1)
            continue

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        # Throttle to ~15fps
        time.sleep(1.0 / 15.0)


@app.get("/snapshot")
async def get_snapshot():
    """MJPEG stream of the processed frame with heatmap overlays."""
    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "product": "StorePulse AI",
        "version": "1.0.0",
        "developer": "Omkar Gurav",
    }


if __name__ == "__main__":
    import uvicorn
    from backend import settings
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
    )
