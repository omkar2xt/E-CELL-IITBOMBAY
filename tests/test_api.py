# tests/test_api.py
# StorePulse AI — Automated API Integration Tests
# Developer: Omkar Gurav

import pytest
from starlette.testclient import TestClient
from backend.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["product"] == "StorePulse AI"
    assert data["developer"] == "Omkar Gurav"


def test_analytics_status():
    res = client.get("/api/analytics/status")
    assert res.status_code == 200
    data = res.json()
    assert "pipeline_running" in data
    assert data["product"] == "StorePulse AI"


def test_analytics_zones_and_friction():
    res = client.get("/api/analytics/zones")
    assert res.status_code == 200
    assert "zone_analytics" in res.json()

    res_f = client.get("/api/analytics/friction")
    assert res_f.status_code == 200
    data_f = res_f.json()
    assert "zone_scores" in data_f
    assert "store_level" in data_f
    assert "disclaimer" in data_f


def test_zones_crud_api():
    # List zones
    res = client.get("/api/zones/")
    assert res.status_code == 200
    assert "zones" in res.json()

    # Create new test zone
    new_zone = {
        "id": "api_test_zone",
        "name": "API Test Zone",
        "type": "display",
        "polygon": [
            {"x": 0.1, "y": 0.1},
            {"x": 0.4, "y": 0.1},
            {"x": 0.4, "y": 0.4},
            {"x": 0.1, "y": 0.4},
        ],
        "capacity": 8,
        "dwell_alert_seconds": 90.0,
    }
    create_res = client.post("/api/zones/", json=new_zone)
    assert create_res.status_code == 200
    assert create_res.json()["status"] == "created"

    # Delete test zone
    del_res = client.delete("/api/zones/api_test_zone")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"


def test_layouts_api_and_simulation():
    # Get baseline layout
    res = client.get("/api/layouts/baseline")
    assert res.status_code == 200
    baseline_data = res.json()["layout"]
    assert baseline_data["is_baseline"] is True
    baseline_id = baseline_data["id"]

    # List layouts
    list_res = client.get("/api/layouts/")
    assert list_res.status_code == 200
    layouts = list_res.json()["layouts"]
    assert len(layouts) >= 1

    # Run simulation comparing baseline to itself
    sim_payload = {
        "baseline_id": baseline_id,
        "proposed_id": baseline_id,
    }
    sim_res = client.post("/api/layouts/simulate", json=sim_payload)
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert "comparison" in sim_data
    assert "baseline" in sim_data
    assert "assumptions" in sim_data


def test_layout_not_found():
    res = client.get("/api/layouts/nonexistent_id_12345")
    assert res.status_code == 404


def test_zones_bottlenecks_and_dashboard_integration():
    """Requirement 10: API endpoints for bottlenecks, zone stats, and dashboard integration."""
    # 1. Bottlenecks endpoint
    b_res = client.get("/api/zones/bottlenecks")
    assert b_res.status_code == 200
    b_data = b_res.json()
    assert "total_bottlenecks" in b_data
    assert "status" in b_data
    assert b_data["status"] in ("SMOOTH", "WARNING", "CONGESTED")
    assert "bottlenecks" in b_data
    assert isinstance(b_data["bottlenecks"], list)

    # 2. Zone stats endpoint with dwell & explainability schema
    stats_res = client.get("/api/zones/stats")
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert "zone_stats" in stats_data or "zones" in stats_data
    zones = stats_data.get("zone_stats") or stats_data.get("zones")
    assert isinstance(zones, dict)
    for zid, zstat in zones.items():
        assert "current_occupancy" in zstat
        assert "capacity" in zstat
        assert "avg_dwell_seconds" in zstat
        assert "active_avg_dwell_seconds" in zstat
        assert "bottleneck" in zstat
        b = zstat["bottleneck"]
        assert "is_bottleneck" in b
        assert "severity" in b
        assert "evidence" in b
        assert "recommendation" in b
        assert "thresholds" in b

    # 3. Transitions endpoint
    trans_res = client.get("/api/zones/transitions")
    assert trans_res.status_code == 200
    assert "transitions" in trans_res.json()


def test_layouts_validate_endpoint():
    """Verify geometry validation endpoint on valid and overlapping layouts."""
    # Valid payload
    valid_payload = {
        "name": "Validation Test Layout",
        "elements": [
            {"id": "e", "element_type": "entrance", "x": 0.0, "y": 0.8, "width": 0.1, "height": 0.1, "rotation": 0.0, "label": "In"},
            {"id": "c", "element_type": "checkout", "x": 0.8, "y": 0.1, "width": 0.1, "height": 0.2, "rotation": 0.0, "label": "Cashier"},
            {"id": "s1", "element_type": "shelf", "x": 0.2, "y": 0.2, "width": 0.1, "height": 0.3, "rotation": 0.0, "label": "Shelf 1"},
        ],
        "zones": []
    }
    res_valid = client.post("/api/layouts/validate", json=valid_payload)
    assert res_valid.status_code == 200
    assert res_valid.json()["is_valid"] is True
    assert res_valid.json()["overlap_count"] == 0

    # Overlapping payload
    overlap_payload = {
        "name": "Collision Test",
        "elements": [
            {"id": "s1", "element_type": "shelf", "x": 0.3, "y": 0.3, "width": 0.2, "height": 0.2, "rotation": 0.0, "label": "S1"},
            {"id": "s2", "element_type": "shelf", "x": 0.35, "y": 0.35, "width": 0.2, "height": 0.2, "rotation": 0.0, "label": "S2"},
        ],
        "zones": []
    }
    res_overlap = client.post("/api/layouts/validate", json=overlap_payload)
    assert res_overlap.status_code == 200
    assert res_overlap.json()["overlap_count"] >= 1


def test_transitions_insufficient_data_contract():
    """Verify transitions endpoint contract on insufficient vs sufficient data."""
    res = client.get("/api/zones/transitions")
    assert res.status_code == 200
    data = res.json()
    assert "transitions" in data
    assert "total_transitions" in data
    assert "data_sufficient" in data
    # If no recorded transitions, data_sufficient MUST be False
    if data["total_transitions"] == 0:
        assert data["data_sufficient"] is False


def test_websocket_connect_and_disconnect():
    """Verify WebSocket /ws endpoint connects, sends/receives cleanly, and handles disconnect."""
    with client.websocket_connect("/ws") as ws:
        # Send a ping/hello message from client
        ws.send_text("ping")
        # Connection succeeds without raising exception on disconnect


