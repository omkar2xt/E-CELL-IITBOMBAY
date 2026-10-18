# StorePulse AI — Real-Time Analytics REST API
# Developer: Omkar Gurav

from fastapi import APIRouter
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.zone_analytics import zone_analytics_engine
from backend.flow_friction import friction_calculator

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/status")
def get_status():
    """Health check and pipeline status."""
    from backend.pipeline import pipeline_runner
    return {
        "pipeline_running": pipeline_runner.is_running,
        "status": "running" if pipeline_runner.is_running else "stopped",
        "product": "StorePulse AI",
        "version": "1.0.0",
    }


@router.get("/metrics")
def get_current_metrics():
    """Get the latest analytics metrics snapshot."""
    from backend.pipeline import pipeline_runner
    metrics = pipeline_runner.get_latest_metrics()
    if metrics is None:
        return {"metrics": None, "message": "No data yet — pipeline starting up or video unavailable"}
    return {"metrics": metrics}


@router.get("/heatmap")
def get_heatmap_data():
    """
    Get heatmap data as a flat array for frontend rendering.
    Returns normalized values 0-255 per pixel region.
    """
    try:
        from backend.pipeline import pipeline_runner
        heatmap_data = pipeline_runner.get_heatmap_data()
        return {"heatmap": heatmap_data}
    except Exception as e:
        return {"heatmap": None, "error": str(e)}


@router.get("/zones")
def get_zone_analytics():
    """Get zone-wise dwell-time and occupancy statistics."""
    return {"zone_analytics": zone_analytics_engine.get_zone_stats()}


@router.get("/movement")
def get_movement_data():
    """Get zone-to-zone transition data for flow visualization."""
    return zone_analytics_engine.get_movement_data()


@router.get("/friction")
def get_friction_scores():
    """Get Flow Friction Scores for all zones."""
    from backend.pipeline import pipeline_runner
    zone_stats = zone_analytics_engine.get_zone_stats()
    metrics = pipeline_runner.get_latest_metrics() or {}
    queue_count = metrics.get("queue_count", 0)
    queue_threshold = 3

    scores = friction_calculator.calculate(zone_stats, queue_count, queue_threshold)
    store_score = friction_calculator.get_store_level_score(scores)

    return {
        "zone_scores": scores,
        "store_level": store_score,
        "disclaimer": (
            "Prototype heuristic metric. Not a validated industry standard. "
            "Calibrate thresholds and weights using observed footage."
        )
    }


@router.get("/history")
def get_history():
    """Get historical occupancy data per zone."""
    zone_stats = zone_analytics_engine.get_zone_stats()
    history = {}
    for zid, stats in zone_stats.items():
        history[zid] = {
            "zone_name": stats.get("zone_name", zid),
            "history": stats.get("history", []),
        }
    return {"history": history}
