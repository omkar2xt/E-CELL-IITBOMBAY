# StorePulse AI — Zone Configuration REST API
# Developer: Omkar Gurav

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Tuple, Optional
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.zone_analytics import Zone, zone_analytics_engine

router = APIRouter(prefix="/api/zones", tags=["zones"])


class ZonePolygonPoint(BaseModel):
    x: float
    y: float


class ZoneCreateRequest(BaseModel):
    id: str
    name: str
    type: str = "display"
    polygon: List[ZonePolygonPoint]
    capacity: int = 10
    dwell_alert_seconds: float = 120.0


class ZoneResponse(BaseModel):
    id: str
    name: str
    type: str
    polygon: List[dict]
    capacity: int
    dwell_alert_seconds: float


def _zone_to_response(zone: Zone) -> dict:
    return {
        "id": zone.id,
        "name": zone.name,
        "type": zone.type,
        "polygon": [{"x": p[0], "y": p[1]} for p in zone.polygon],
        "capacity": zone.capacity,
        "dwell_alert_seconds": zone.dwell_alert_seconds,
    }


@router.get("/")
def list_zones():
    """List all configured zones."""
    zones = zone_analytics_engine.get_zones()
    return {"zones": [_zone_to_response(z) for z in zones]}


@router.post("/")
def create_zone(req: ZoneCreateRequest):
    """Create or replace a zone."""
    polygon = [(p.x, p.y) for p in req.polygon]
    if len(polygon) < 3:
        raise HTTPException(status_code=400, detail="Polygon must have at least 3 points")
    zone = Zone(
        id=req.id,
        name=req.name,
        type=req.type,
        polygon=polygon,
        capacity=req.capacity,
        dwell_alert_seconds=req.dwell_alert_seconds,
    )
    zone_analytics_engine.add_zone(zone)
    return {"status": "created", "zone": _zone_to_response(zone)}


@router.put("/{zone_id}")
def update_zone(zone_id: str, req: ZoneCreateRequest):
    """Update an existing zone."""
    polygon = [(p.x, p.y) for p in req.polygon]
    zone = Zone(
        id=zone_id,
        name=req.name,
        type=req.type,
        polygon=polygon,
        capacity=req.capacity,
        dwell_alert_seconds=req.dwell_alert_seconds,
    )
    zone_analytics_engine.add_zone(zone)
    return {"status": "updated", "zone": _zone_to_response(zone)}


@router.delete("/{zone_id}")
def delete_zone(zone_id: str):
    """Delete a zone."""
    zone_analytics_engine.remove_zone(zone_id)
    return {"status": "deleted", "zone_id": zone_id}


@router.get("/stats")
def get_zone_stats():
    """Get current dwell-time and occupancy statistics for all zones."""
    return {"zone_stats": zone_analytics_engine.get_zone_stats()}


@router.get("/bottlenecks")
def get_bottlenecks():
    """Get explainable bottleneck analysis and alerts across all zones."""
    return zone_analytics_engine.get_bottleneck_summary()


@router.get("/transitions")
def get_zone_transitions():
    """Get zone-to-zone transition counts."""
    return zone_analytics_engine.get_transitions()



@router.post("/reset")
def reset_zone_analytics():
    """Reset all zone analytics data."""
    zone_analytics_engine.reset()
    return {"status": "reset"}


@router.post("/defaults")
def load_default_zones():
    """Load a set of default zones for a typical retail store."""
    defaults = Zone.__class__.__mro__  # just verify import
    from backend.zone_analytics import ZoneAnalyticsEngine
    defaults = ZoneAnalyticsEngine.default_zones()
    zone_analytics_engine.set_zones(defaults)
    return {"status": "loaded", "count": len(defaults)}
