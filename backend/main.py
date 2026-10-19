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
from backend.routers import zones, layouts, analytics as analytics_router, alerts as alerts_router
from backend.database.init_db import init_database
from backend.database.connection import IS_POSTGRES

# Runtime environment detection
IS_SERVERLESS = os.getenv("VERCEL") == "1" or os.getenv("SERVERLESS", "0") == "1" or os.getenv("API_ONLY", "0") == "1"


async def broadcast_worker():
    while True:
        payload = pipeline_runner.get_latest_metrics()
        if payload is not None:
            await manager.broadcast(payload)
            pipeline_runner.clear_latest_metrics()
        await asyncio.sleep(0.1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[StorePulse AI] Initializing database schema...")
    try:
        init_database()
    except Exception as e:
        print(f"[StorePulse AI] Warning: Database initialization warning: {e}")

    task = None
    if not IS_SERVERLESS:
        print("[StorePulse AI] Persistent worker runtime active — starting CV analytics pipeline...")
        pipeline_runner.start()
        task = asyncio.create_task(broadcast_worker())
    else:
        print("[StorePulse AI] Serverless runtime active (Vercel) — continuous video worker loop disabled.")

    yield

    if task:
        task.cancel()
    if not IS_SERVERLESS:
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
app.include_router(alerts_router.router)


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
    """MJPEG stream of the processed frame with heatmap overlays or single snapshot on serverless."""
    if IS_SERVERLESS:
        frame = pipeline_runner.get_latest_snapshot()
        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                from fastapi.responses import Response
                return Response(content=buffer.tobytes(), media_type="image/jpeg")
        from fastapi.responses import Response
        return Response(
            content=b'{"status": "serverless_active", "message": "Live video processing worker runs on persistent runtime."}',
            status_code=200,
            media_type="application/json"
        )

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/health")
async def health():
    """Health check endpoint with pipeline telemetry and runtime mode."""
    return {
        "status": "ok",
        "product": "StorePulse AI",
        "version": "1.0.0",
        "developer": "Omkar Gurav",
        "runtime": "serverless" if IS_SERVERLESS else "persistent_worker",
        "pipeline": {
            "running": pipeline_runner.is_running if not IS_SERVERLESS else False,
            "connection_status": getattr(pipeline_runner, "connection_status", "unknown") if not IS_SERVERLESS else "serverless",
            "source_type": getattr(pipeline_runner, "source_type", "unknown"),
            "is_demo": getattr(pipeline_runner, "is_demo", False),
            "error_message": getattr(pipeline_runner, "error_message", None),
        }
    }


@app.get("/api/health/storage")
def storage_health():
    """Storage and database health telemetry without exposing secrets."""
    from backend.alerts.storage import storage_manager
    from backend.database.connection import SessionLocal
    from backend.database.models import AlertEvent, EvidenceSnapshot
    db = SessionLocal()
    try:
        alert_count = db.query(AlertEvent).count()
        snapshot_count = db.query(EvidenceSnapshot).count()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
        alert_count = 0
        snapshot_count = 0
    finally:
        db.close()

    storage_stats = storage_manager.get_storage_stats()
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "runtime": "serverless" if IS_SERVERLESS else "persistent_worker",
        "database": {
            "status": db_status,
            "engine": "neon_postgresql" if IS_POSTGRES else "sqlite_wal",
            "total_alerts": alert_count,
            "total_snapshots": snapshot_count
        },
        "storage": storage_stats
    }


from pydantic import BaseModel

class SourceSwitchRequest(BaseModel):
    source: str


@app.get("/api/pipeline/source")
def get_pipeline_source():
    """Get active pipeline input source and execution mode."""
    return {
        "source": str(pipeline_runner.source),
        "source_type": getattr(pipeline_runner, "source_type", "unknown"),
        "is_demo": getattr(pipeline_runner, "is_demo", False),
        "connection_status": getattr(pipeline_runner, "connection_status", "unknown"),
        "running": pipeline_runner.is_running,
    }


@app.post("/api/pipeline/source")
def switch_pipeline_source(req: SourceSwitchRequest):
    """Switch pipeline between demo simulation, local video file, or camera."""
    src = req.source.strip()
    if src.lower() in ("demo", "simulation"):
        pipeline_runner.switch_source("demo")
    elif src.lower() in ("video", "file", "default"):
        default_vid = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'detection', 'vid', 'retail-cctv-footage.mp4'))
        pipeline_runner.switch_source(default_vid)
    else:
        pipeline_runner.switch_source(src)
    return {
        "status": "switched",
        "source": str(pipeline_runner.source),
        "source_type": pipeline_runner.source_type,
        "is_demo": pipeline_runner.is_demo,
    }


@app.post("/api/pipeline/reset")
def reset_pipeline():
    """Reset zone analytics and tracking memory."""
    from backend.zone_analytics import zone_analytics_engine
    from backend.pipeline import pipeline_runner
    pipeline_runner.reset_session()
    zone_analytics_engine.reset()
    return {"status": "reset", "message": "Pipeline, counter, and zone analytics state reset successfully"}




if __name__ == "__main__":
    import uvicorn
    from backend import settings
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
    )
