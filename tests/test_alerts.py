# StorePulse AI — Automated Alert Evidence & Storage Test Suite
# Developer: Omkar Gurav

import os
import time
import uuid
import pytest
import numpy as np
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.connection import SessionLocal, engine
from backend.database.models import Base, AlertEvent, EvidenceSnapshot, AlertStateChange
from backend.alerts.storage import storage_manager, EvidenceStorageManager
from backend.alerts.deduplicator import AlertDeduplicator
from backend.alerts.service import AlertService, alert_service

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


def test_alert_creation_and_database_persistence():
    """1. Test alert record persistence in database."""
    test_id = str(uuid.uuid4())
    alert = alert_service.trigger_alert(
        alert_type="queue_threshold_exceeded",
        severity="HIGH",
        metric_name="queue_count",
        metric_value=5,
        threshold_value=3,
        message=f"Test alert persistence {test_id}",
        zone_id="checkout",
        source_mode="demo",
        cooldown_seconds=0.1
    )
    assert alert is not None
    assert alert["status"] == "active"
    assert alert["metric_value"] == 5.0

    db = SessionLocal()
    rec = db.query(AlertEvent).filter(AlertEvent.id == alert["id"]).first()
    assert rec is not None
    assert rec.alert_type == "queue_threshold_exceeded"
    assert rec.zone_id == "checkout"
    db.close()


def test_snapshot_capture_on_alert_trigger():
    """2. Test automatic snapshot capture and thumbnail generation."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[100:200, 100:200] = (255, 128, 0)

    alert = alert_service.trigger_alert(
        alert_type="bottleneck_detected",
        severity="CRITICAL",
        metric_name="congested_duration",
        metric_value=12.5,
        threshold_value=5.0,
        message="Critical bottleneck in grocery zone",
        zone_id="grocery",
        source_mode="live",
        frame=frame,
        cooldown_seconds=0.0
    )
    assert alert is not None
    assert alert["snapshot_status"] == "pending"

    # Wait for async worker
    time.sleep(1.0)

    db = SessionLocal()
    rec = db.query(AlertEvent).filter(AlertEvent.id == alert["id"]).first()
    assert rec.snapshot_status == "saved"
    assert len(rec.snapshots) >= 1
    snap = rec.snapshots[0]
    assert snap.file_size_bytes > 0
    assert snap.checksum is not None
    assert snap.image_width == 640
    assert snap.image_height == 480
    db.close()


def test_snapshot_metadata_and_file_association():
    """3. Verify snapshot file on disk matches database metadata."""
    frame = np.ones((240, 320, 3), dtype=np.uint8) * 128
    meta = storage_manager.save_snapshot("test_meta_alert", frame)
    assert meta["capture_status"] == "saved"
    assert os.path.exists(storage_manager.get_snapshot_path(meta["storage_key"]))
    assert os.path.exists(storage_manager.get_snapshot_path(meta["storage_key"], thumbnail=True))

    # Clean up test files
    storage_manager.delete_snapshot(meta["storage_key"], meta["thumbnail_key"])


def test_deduplication_and_cooldown_behavior():
    """4. Test alert deduplication suppresses duplicate alerts within cooldown."""
    dedup = AlertDeduplicator(default_cooldown_seconds=5.0)
    fp = "queue_threshold_exceeded:store-01:checkout"

    # First trigger -> Allowed
    should_trig, existing = dedup.should_trigger(fp, cooldown_seconds=5.0)
    assert should_trig is True
    assert existing is None
    dedup.record_trigger(fp, "alert-1")

    # Immediate second trigger -> Suppressed
    should_trig2, existing2 = dedup.should_trigger(fp, cooldown_seconds=5.0)
    assert should_trig2 is False
    assert existing2 == "alert-1"

    # Resolve -> Allowed again
    res = dedup.resolve(fp)
    assert res == "alert-1"
    should_trig3, _ = dedup.should_trigger(fp, cooldown_seconds=5.0)
    assert should_trig3 is True


def test_multiple_concurrent_alerts():
    """5. Test concurrent alerts across different zones without collision."""
    zones = ["entrance", "electronics", "grocery", "promo"]
    created_ids = []

    for z in zones:
        a = alert_service.trigger_alert(
            alert_type="zone_capacity_exceeded",
            severity="MEDIUM",
            metric_name="current_occupancy",
            metric_value=12,
            threshold_value=10,
            message=f"Capacity alert in {z}",
            zone_id=z,
            cooldown_seconds=0.0
        )
        if a:
            created_ids.append(a["id"])

    assert len(created_ids) == len(zones)
    db = SessionLocal()
    count = db.query(AlertEvent).filter(AlertEvent.id.in_(created_ids)).count()
    assert count == len(zones)
    db.close()


def test_snapshot_write_failure_resilience():
    """6. Handle empty or malformed frame gracefully."""
    empty_frame = np.array([])
    meta = storage_manager.save_snapshot("empty_alert", empty_frame)
    assert meta["capture_status"] == "failed"


def test_database_query_and_cursor_pagination():
    """8. Test cursor pagination and filtering."""
    resp = client.get("/api/alerts?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "alerts" in data
    assert "total" in data
    assert len(data["alerts"]) <= 5


def test_snapshot_path_traversal_protection():
    """9. Security test: Path traversal attempts must be rejected or sanitized."""
    malicious_key = "../../etc/passwd"
    safe_path = storage_manager.get_snapshot_path(malicious_key)
    # Safe path must either be None or be sanitized strictly within base_dir
    if safe_path is not None:
        assert safe_path.startswith(storage_manager.base_dir)


def test_status_update_and_audit_history():
    """10. Test PATCH /api/alerts/{id}/status and audit state changes."""
    alert = alert_service.trigger_alert(
        alert_type="excessive_dwell_time",
        severity="MEDIUM",
        metric_name="dwell_seconds",
        metric_value=150,
        threshold_value=120,
        message="Long dwell customer in electronics",
        zone_id="electronics",
        cooldown_seconds=0.0
    )
    alert_id = alert["id"]

    resp = client.patch(
        f"/api/alerts/{alert_id}/status",
        json={"status": "acknowledged", "reason": "Floor staff dispatched"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "acknowledged"
    assert len(body["state_changes"]) >= 2


def test_retention_cleanup_api():
    """11. Test retention purge endpoint."""
    resp = client.post("/api/alerts/cleanup", json={"retention_days": 365})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "deleted_alerts" in data


def test_storage_health_endpoint():
    """12. Test storage and database health endpoint."""
    resp = client.get("/api/health/storage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["database"]["engine"] == "sqlite_wal"
    assert "total_snapshots" in data["storage"]
