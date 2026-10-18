# StorePulse AI — Layouts & Simulation REST API
# Developer: Omkar Gurav

import uuid
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.simulator import LayoutConfig, ShelfElement, layout_store, layout_simulator
from backend.zone_analytics import zone_analytics_engine

router = APIRouter(prefix="/api/layouts", tags=["layouts"])


# ── Request / Response models ─────────────────────────────────────────


class ShelfElementModel(BaseModel):
    id: str
    element_type: str
    x: float
    y: float
    width: float
    height: float
    rotation: float = 0.0
    label: str = ""


class ZoneModel(BaseModel):
    id: str
    name: str
    type: str
    polygon: List[Dict[str, float]]
    capacity: int = 10


class LayoutCreateRequest(BaseModel):
    id: Optional[str] = None
    name: str
    description: str = ""
    elements: List[ShelfElementModel] = []
    zones: List[ZoneModel] = []
    is_baseline: bool = False


class SimulationRequest(BaseModel):
    baseline_id: str
    proposed_id: str


# ── Helpers ───────────────────────────────────────────────────────────


def _model_to_shelf(m: ShelfElementModel) -> ShelfElement:
    return ShelfElement(
        id=m.id,
        element_type=m.element_type,
        x=m.x,
        y=m.y,
        width=m.width,
        height=m.height,
        rotation=m.rotation,
        label=m.label,
    )


def _layout_to_dict(layout: LayoutConfig) -> Dict:
    return {
        "id": layout.id,
        "name": layout.name,
        "description": layout.description,
        "is_baseline": layout.is_baseline,
        "created_at": layout.created_at,
        "element_count": len(layout.elements),
        "zone_count": len(layout.zones),
        "elements": [
            {
                "id": e.id,
                "element_type": e.element_type,
                "x": e.x, "y": e.y,
                "width": e.width, "height": e.height,
                "rotation": e.rotation,
                "label": e.label,
            }
            for e in layout.elements
        ],
        "zones": layout.zones,
    }


# ── Endpoints ─────────────────────────────────────────────────────────


@router.get("/")
def list_layouts():
    """List all saved layouts."""
    return {"layouts": layout_store.list_layouts()}


@router.post("/")
def create_layout(req: LayoutCreateRequest):
    """Create a new layout."""
    layout_id = req.id or str(uuid.uuid4())[:8]
    shelves = [_model_to_shelf(e) for e in req.elements]
    zones = [z.model_dump() for z in req.zones]

    layout = LayoutConfig(
        id=layout_id,
        name=req.name,
        description=req.description,
        elements=shelves,
        zones=zones,
        is_baseline=req.is_baseline,
    )
    saved = layout_store.save_layout(layout)
    return {"status": "created", "layout": _layout_to_dict(saved)}


@router.get("/baseline")
def get_baseline():
    """Get the current baseline layout."""
    baseline = layout_store.get_baseline()
    if not baseline:
        raise HTTPException(status_code=404, detail="No baseline layout found")
    return {"layout": _layout_to_dict(baseline)}


@router.get("/{layout_id}")
def get_layout(layout_id: str):
    """Get a specific layout by ID."""
    layout = layout_store.get_layout(layout_id)
    if not layout:
        raise HTTPException(status_code=404, detail=f"Layout '{layout_id}' not found")
    return {"layout": _layout_to_dict(layout)}


@router.put("/{layout_id}")
def update_layout(layout_id: str, req: LayoutCreateRequest):
    """Update an existing layout."""
    existing = layout_store.get_layout(layout_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Layout '{layout_id}' not found")

    shelves = [_model_to_shelf(e) for e in req.elements]
    zones = [z.model_dump() for z in req.zones]

    layout = LayoutConfig(
        id=layout_id,
        name=req.name,
        description=req.description,
        elements=shelves,
        zones=zones,
        is_baseline=req.is_baseline,
        created_at=existing.created_at,
    )
    saved = layout_store.save_layout(layout)
    return {"status": "updated", "layout": _layout_to_dict(saved)}


@router.delete("/{layout_id}")
def delete_layout(layout_id: str):
    """Delete a layout. Cannot delete the baseline."""
    success = layout_store.delete_layout(layout_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot delete baseline layout or layout not found")
    return {"status": "deleted", "layout_id": layout_id}


@router.post("/simulate")
def run_simulation(req: SimulationRequest):
    """
    Run a heuristic simulation comparing baseline vs. proposed layout.
    Returns a comparison report with clearly labeled estimates.
    """
    baseline = layout_store.get_layout(req.baseline_id)
    proposed = layout_store.get_layout(req.proposed_id)

    if not baseline:
        raise HTTPException(status_code=404, detail=f"Baseline layout '{req.baseline_id}' not found")
    if not proposed:
        raise HTTPException(status_code=404, detail=f"Proposed layout '{req.proposed_id}' not found")

    # Include real analytics if available
    try:
        real_analytics = zone_analytics_engine.get_zone_stats()
        if not real_analytics:
            real_analytics = None
    except Exception:
        real_analytics = None

    result = layout_simulator.simulate(baseline, proposed, real_analytics)
    return result
