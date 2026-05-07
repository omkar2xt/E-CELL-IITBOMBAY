from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import cv2
import asyncio
import sys
import os

# Tambahkan root directory ke sys.path agar import 'backend' berhasil walau di-run dari mana saja
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.ws_manager import manager
from backend.pipeline import pipeline_runner

async def broadcast_worker():
    while True:
        payload = pipeline_runner.get_latest_metrics()
        if payload is not None:
            await manager.broadcast(payload)
            pipeline_runner.clear_latest_metrics()
        await asyncio.sleep(0.1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start pipeline on startup
    print("[App] Starting analytics pipeline...")
    pipeline_runner.start()
    task = asyncio.create_task(broadcast_worker())
    yield
    # Stop pipeline on shutdown
    task.cancel()
    print("[App] Stopping analytics pipeline...")
    pipeline_runner.stop()

app = FastAPI(title="Retail Analytics API", lifespan=lifespan)

# Allow CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We just wait for messages, but we don't really expect any from the client
            # The server pushes data to the client via manager.broadcast()
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

def frame_generator():
    """Generator function that yields JPEG frames for MJPEG streaming."""
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
               
        # Throttle stream to ~15fps to save bandwidth
        time.sleep(1.0 / 15.0)

import time

@app.get("/snapshot")
async def get_snapshot():
    """Returns an MJPEG stream of the latest heatmap frames."""
    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

if __name__ == "__main__":
    import uvicorn
    from backend import settings
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
