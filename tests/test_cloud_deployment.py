# StorePulse AI — Cloud Deployment & Data Migration Verification Tests
# Developer: Omkar Gurav

import os
import io
import time
import uuid
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.connection import (
    normalize_database_url, create_app_engine, get_migration_engine,
    DATABASE_URL, DIRECT_URL, IS_POSTGRES
)
from backend.database.models import AlertEvent, EvidenceSnapshot, Base
from backend.alerts.storage import EvidenceStorageManager, storage_manager
from backend.alerts.service import AlertService, alert_service
from backend.scripts.migrate_snapshots_to_blob import run_migration

client = TestClient(app)


def test_database_url_normalization():
    """Verify postgres:// is rewritten to postgresql:// for modern SQLAlchemy."""
    assert normalize_database_url("postgres://user:pass@ep-pooler.neon.tech/neondb") == \
           "postgresql://user:pass@ep-pooler.neon.tech/neondb"
    assert normalize_database_url("postgresql://user:pass@ep.neon.tech/neondb") == \
           "postgresql://user:pass@ep.neon.tech/neondb"
    assert normalize_database_url("sqlite:///data.db") == "sqlite:///data.db"
    assert normalize_database_url("") == ""


def test_cloud_engine_pooling_parameters():
    """Verify Neon pooled connection engine creates QueuePool with serverless pre-ping and recycling."""
    fake_pg_url = "postgresql://user:pass@ep-pooler.neon.tech/neondb"
    engine = create_app_engine(fake_pg_url)
    assert engine.dialect.name == "postgresql"
    assert engine.pool._pre_ping is True
    assert engine.pool._recycle == 300


def test_direct_migration_engine():
    """Verify migration engine returns valid connectable."""
    engine = get_migration_engine()
    assert engine is not None


def test_evidence_storage_private_blob_upload_and_download():
    """Verify Vercel Blob private access integration and retrieval."""
    test_manager = EvidenceStorageManager()
    test_manager.blob_token = "mock_blob_token_xyz"
    test_manager.blob_access = "private"

    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    dummy_frame[20:80, 20:80] = [0, 255, 0]
    alert_id = str(uuid.uuid4())

    mock_put_result = MagicMock()
    mock_put_result.pathname = f"snapshots/{alert_id}_full.jpg"
    mock_put_result.url = f"https://blob.vercel-storage.com/snapshots/{alert_id}_full.jpg"

    mock_get_result = MagicMock()
    mock_get_result.body = b"mock_jpeg_bytes_payload"

    with patch("vercel.blob.sync.put_blob", return_value=mock_put_result) as mock_put:
        with patch("vercel.blob.sync.get_blob", return_value=mock_get_result) as mock_get:
            # 1. Save snapshot
            meta = test_manager.save_snapshot(alert_id, dummy_frame)
            assert meta["capture_status"] == "saved"
            assert meta["storage_key"] == f"snapshots/{alert_id}_full.jpg"
            assert meta["checksum"] is not None
            mock_put.assert_called()

            # 2. Retrieve snapshot bytes (authenticated backend fetch)
            data, mime = test_manager.get_snapshot_bytes(meta["storage_key"])
            assert data == b"mock_jpeg_bytes_payload"
            assert mime == "image/jpeg"
            mock_get.assert_called_with(f"snapshots/{alert_id}_full.jpg", access="private")


def test_failure_recovery_on_cloud_blob_upload_error():
    """Verify that if Vercel Blob upload fails, alert is preserved and local storage is retained."""
    test_manager = EvidenceStorageManager()
    test_manager.blob_token = "mock_blob_token"
    test_manager.blob_access = "private"

    dummy_frame = np.ones((60, 60, 3), dtype=np.uint8) * 128
    alert_id = str(uuid.uuid4())

    # Simulate network or credential error from Vercel Blob
    with patch("vercel.blob.sync.put_blob", side_effect=RuntimeError("Vercel Blob Connection Timeout")):
        meta = test_manager.save_snapshot(alert_id, dummy_frame)

        # Alert snapshot is STILL saved locally! Alert is never dropped!
        assert meta["capture_status"] == "saved"
        assert meta["storage_key"] == f"{alert_id}_full.jpg"
        assert meta["checksum"] is not None

        # Verify local file exists on disk
        local_path = test_manager.get_snapshot_path(meta["storage_key"])
        assert local_path is not None
        assert os.path.exists(local_path)

        # Cleanup test file
        test_manager.delete_snapshot(meta["storage_key"], meta.get("thumbnail_key"))


def test_snapshot_path_manipulation_prevention():
    """Verify directory traversal is prevented in snapshot storage."""
    mgr = EvidenceStorageManager()
    with pytest.raises(ValueError):
        mgr._resolve_safe_path("../../../etc/passwd")

    with pytest.raises(ValueError):
        mgr._resolve_safe_path("")


def test_alert_snapshot_delivery_endpoint_security():
    """Verify API endpoint serves snapshot securely without leaking credentials."""
    dummy_frame = np.zeros((80, 80, 3), dtype=np.uint8)
    created = alert_service.trigger_alert(
        alert_type="bottleneck",
        severity="HIGH",
        metric_name="dwell_time",
        metric_value=150.0,
        threshold_value=120.0,
        message="Cloud deployment test alert",
        frame=dummy_frame,
        cooldown_seconds=0.0
    )
    assert created is not None
    alert_id = created["id"]

    # Allow worker thread to persist snapshot
    time.sleep(0.5)

    # Request snapshot via public API
    res = client.get(f"/api/alerts/{alert_id}/snapshot")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/jpeg"
    assert "Cache-Control" in res.headers
    assert res.headers.get("X-Alert-ID") == alert_id

    # Ensure no secrets leaked in headers
    header_str = str(res.headers)
    assert "BLOB_READ_WRITE_TOKEN" not in header_str
    assert "token" not in header_str.lower() or "csrf" in header_str.lower()


def test_serverless_runtime_mode_telemetry():
    """Verify health endpoint reports runtime capability and database status."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert "runtime" in data
    assert data["runtime"] in ("serverless", "persistent_worker")

    res_storage = client.get("/api/health/storage")
    assert res_storage.status_code == 200
    s_data = res_storage.json()
    assert s_data["status"] == "healthy"
    assert "database" in s_data
    assert "storage" in s_data
    assert s_data["storage"]["status"] == "healthy"


def test_snapshot_resumable_migration_dry_run():
    """Verify snapshot migration script dry run executes and reports correctly."""
    result = run_migration(dry_run=True, limit=5, access="private")
    assert result["status"] == "completed"
    assert result["migrated"] >= 0
    assert result["failed"] == 0
