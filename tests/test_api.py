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
