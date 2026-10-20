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


@router.post("/validate")
def validate_layout_endpoint(req: LayoutCreateRequest):
    """
    Validate layout geometry for out-of-bounds fixtures and aisle-blocking overlaps.
    """
    shelves = [_model_to_shelf(e) for e in req.elements]
    zones = [z.model_dump() for z in req.zones]
    layout = LayoutConfig(
        id=req.id or "temp_validate",
        name=req.name,
        description=req.description,
        elements=shelves,
        zones=zones,
    )
    return layout_simulator.validate_layout(layout)


@router.post("/simulate")
def run_simulation(req: SimulationRequest):
    """
    Run a heuristic simulation comparing baseline vs. proposed layout.
    Incorporates real analytics and empirical transition probabilities where available.
    Returns a comparison report with clearly labeled estimates.
    """
    baseline = layout_store.get_layout(req.baseline_id)
    proposed = layout_store.get_layout(req.proposed_id)

    if not baseline:
        raise HTTPException(status_code=404, detail=f"Baseline layout '{req.baseline_id}' not found")
    if not proposed:
        raise HTTPException(status_code=404, detail=f"Proposed layout '{req.proposed_id}' not found")

    # Include real analytics and transitions if available
    try:
        real_analytics = zone_analytics_engine.get_zone_stats()
        if not real_analytics:
            real_analytics = None
    except Exception:
        real_analytics = None

    try:
        transition_data = zone_analytics_engine.get_transitions()
        if not transition_data or not transition_data.get("transitions"):
            transition_data = None
    except Exception:
        transition_data = None

    result = layout_simulator.simulate(baseline, proposed, real_analytics, transition_data)

    b_m = result.get("baseline", {}).get("metrics", {})
    p_m = result.get("proposed", {}).get("metrics", {})
    b_dist = b_m.get("avg_weighted_walking_distance", 1.0)
    p_dist = p_m.get("avg_weighted_walking_distance", 1.0)
    walking_diff_pct = round(((p_dist - b_dist) / max(b_dist, 0.001)) * 100, 1)

    conflict_score = float(p_m.get("route_conflict_score", 0.0))
    bottleneck_risk_score = float(p_m.get("bottleneck_risk_index", 0.0))
    space_utilization_score = float(p_m.get("space_utilization_pct", 0.0))
    flow_friction_index = float(p_m.get("estimated_layout_friction", 0.0))
    overall_score = round(max(0.0, min(100.0, 100.0 - (flow_friction_index * 0.4 + bottleneck_risk_score * 0.4 + conflict_score * 0.2))), 1)

    result["overall_score"] = overall_score
    result["walking_distance_change_pct"] = walking_diff_pct
    result["conflict_score"] = conflict_score
    result["bottleneck_risk_score"] = bottleneck_risk_score
    result["space_utilization_score"] = space_utilization_score
    result["flow_friction_index"] = flow_friction_index

    # Persist simulation result to database
    try:
        import json
        from backend.database.connection import get_db_context
        from backend.database.models import SimulationResultModel

        sim_id = str(uuid.uuid4())
        is_synthetic = bool(result.get("is_synthetic", True) or real_analytics is None)

        with get_db_context() as db:
            sim_record = SimulationResultModel(
                id=sim_id,
                baseline_id=req.baseline_id,
                proposed_id=req.proposed_id,
                is_synthetic=is_synthetic,
                overall_score=overall_score,
                walking_distance_change_pct=walking_diff_pct,
                conflict_score=conflict_score,
                bottleneck_risk_score=bottleneck_risk_score,
                space_utilization_score=space_utilization_score,
                flow_friction_index=flow_friction_index,
                zone_metrics_json=json.dumps(result.get("zone_comparisons", [])),
                details_json=json.dumps(result),
                created_at=time.time()
            )
            db.add(sim_record)
        result["simulation_id"] = sim_id
        result["persisted"] = True
    except Exception as e:
        result["persisted"] = False
        result["persistence_warning"] = str(e)

    return result


@router.get("/simulations/history")
def get_simulation_history(limit: int = 20):
    """Retrieve persisted What-If simulation history."""
    try:
        import json
        from backend.database.connection import get_db_context
        from backend.database.models import SimulationResultModel

        with get_db_context() as db:
            rows = db.query(SimulationResultModel).order_by(SimulationResultModel.created_at.desc()).limit(limit).all()
            return {
                "count": len(rows),
                "history": [
                    {
                        "id": r.id,
                        "baseline_id": r.baseline_id,
                        "proposed_id": r.proposed_id,
                        "is_synthetic": r.is_synthetic,
                        "overall_score": r.overall_score,
                        "walking_distance_change_pct": r.walking_distance_change_pct,
                        "flow_friction_index": r.flow_friction_index,
                        "created_at": r.created_at,
                        "zone_metrics": json.loads(r.zone_metrics_json or "{}")
                    }
                    for r in rows
                ]
            }
    except Exception as e:
        return {"count": 0, "history": [], "error": str(e)}

