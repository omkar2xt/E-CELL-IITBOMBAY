# StorePulse AI — Production Migration & Supabase/Railway Verification Tests
# Developer: Omkar Gurav

import os
import json
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.simulator import LayoutConfig, ShelfElement, LayoutStore, layout_store, layout_simulator
from backend.database.connection import get_db_context
from backend.database.models import LayoutModel, SimulationResultModel, AnalyticsSnapshotModel

client = TestClient(app)


def test_layout_persistence_across_cache_reload():
    """Verify layouts persist into database and survive in-memory cache clearing (server restart simulation)."""
    unique_id = f"test_layout_{uuid.uuid4().hex[:6]}"
    layout = LayoutConfig(
        id=unique_id,
        name="Persistent Test Layout",
        description="Testing database persistence across restarts",
        elements=[
            ShelfElement(
                id="shelf_p1",
                element_type="shelf",
                x=0.3,
                y=0.2,
                width=0.1,
                height=0.4,
                rotation=0.0,
                label="Perishable Goods"
            )
        ],
        zones=[{"id": "zone_perishable", "name": "Perishable", "type": "grocery"}],
        is_baseline=False
    )

    # 1. Save via layout_store
    layout_store.save_layout(layout)

    # 2. Verify directly in database via SQLAlchemy
    with get_db_context() as db:
        db_record = db.query(LayoutModel).filter(LayoutModel.id == unique_id).first()
        assert db_record is not None
        assert db_record.name == "Persistent Test Layout"
        elements = json.loads(db_record.elements_json)
        assert len(elements) == 1
        assert elements[0]["label"] == "Perishable Goods"

    # 3. Simulate Server Restart: Instantiate brand new LayoutStore from DB
    restarted_store = LayoutStore()
    reloaded_layout = restarted_store.get_layout(unique_id)
    assert reloaded_layout is not None
    assert reloaded_layout.name == "Persistent Test Layout"
    assert len(reloaded_layout.elements) == 1

    # Cleanup
    layout_store.delete_layout(unique_id)


def test_simulation_execution_and_result_persistence():
    """Verify running a simulation persists results into simulation_results table."""
    baseline = layout_store.get_baseline()
    assert baseline is not None

    proposed_id = f"prop_{uuid.uuid4().hex[:6]}"
    proposed = LayoutConfig(
        id=proposed_id,
        name="Proposed Test Layout",
        description="Optimized checkout layout",
        elements=[
            ShelfElement("s_opt1", "shelf", 0.4, 0.2, 0.1, 0.3, label="Shelf"),
            ShelfElement("c_opt1", "checkout", 0.1, 0.1, 0.15, 0.35, label="Checkout"),
            ShelfElement("e_opt1", "entrance", 0.0, 0.8, 0.1, 0.2, label="Entrance"),
        ],
        zones=[]
    )
    layout_store.save_layout(proposed)

    # Execute simulation via API
    res = client.post("/api/layouts/simulate", json={
        "baseline_id": baseline.id,
        "proposed_id": proposed_id
    })
    assert res.status_code == 200
    data = res.json()
    assert "overall_score" in data
    assert "walking_distance_change_pct" in data
    assert "persisted" in data
    assert data["persisted"] is True
    sim_id = data.get("simulation_id")
    assert sim_id is not None

    # Verify simulation report is saved in database
    with get_db_context() as db:
        saved_sim = db.query(SimulationResultModel).filter(SimulationResultModel.id == sim_id).first()
        assert saved_sim is not None
        assert saved_sim.baseline_id == baseline.id
        assert saved_sim.proposed_id == proposed_id

    # Verify history retrieval endpoint
    history_res = client.get("/api/layouts/simulations/history?limit=10")
    assert history_res.status_code == 200
    h_data = history_res.json()
    assert h_data["count"] >= 1
    assert any(h["id"] == sim_id for h in h_data["history"])

    # Cleanup
    layout_store.delete_layout(proposed_id)


def test_synthetic_vs_real_data_labeling():
    """Confirm simulation results distinguish synthetic/heuristic estimates from empirical observations."""
    baseline = layout_store.get_baseline()
    assert baseline is not None

    sim_report = layout_simulator.simulate(baseline, baseline, baseline_analytics=None, transition_data=None)
    # Must be explicitly labeled as heuristic/synthetic
    assert sim_report.get("is_synthetic") is True
    assert "assumptions" in sim_report or "estimation_metadata" in sim_report


def test_railway_cors_and_health_endpoint():
    """Verify health endpoint returns status, version, and runtime capability for Railway."""
    res = client.get("/health")
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] == "ok"
    assert "runtime" in payload
    assert payload["version"] == "1.0.0"


def test_analytics_snapshot_model_integrity():
    """Verify analytics snapshot table stores periodic store flow metrics."""
    snap_id = str(uuid.uuid4())
    with get_db_context() as db:
        snap = AnalyticsSnapshotModel(
            id=snap_id,
            store_id="store-01",
            total_in=45,
            total_out=38,
            current_occupancy=7,
            flow_friction_score=14.2,
            active_dwell_time_avg=88.5,
            zones_data_json=json.dumps({"checkout": {"count": 2, "avg_dwell": 45.0}}),
            is_demo=False
        )
        db.add(snap)

    with get_db_context() as db:
        retrieved = db.query(AnalyticsSnapshotModel).filter(AnalyticsSnapshotModel.id == snap_id).first()
        assert retrieved is not None
        assert retrieved.current_occupancy == 7
        assert retrieved.total_in == 45
        assert retrieved.is_demo is False
        db.delete(retrieved)
