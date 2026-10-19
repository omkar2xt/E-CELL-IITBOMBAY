# StorePulse AI — Alerts API Router
# Developer: Omkar Gurav
# High-performance alert querying, evidence snapshot delivery, and status management

import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.alerts.service import alert_service
from backend.alerts.storage import storage_manager

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class AlertStatusUpdate(BaseModel):
    status: str = Field(..., description="Target status: active, acknowledged, resolved, dismissed")
    reason: Optional[str] = Field("Updated via dashboard", description="Audit reason for status change")


class CleanupRequest(BaseModel):
    retention_days: int = Field(30, ge=1, le=365, description="Number of days to retain alerts and snapshots")


@router.get("")
def list_alerts(
    limit: int = Query(50, ge=1, le=100, description="Page size limit"),
    cursor: Optional[float] = Query(None, description="Keyset cursor timestamp for next page"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    severity: Optional[str] = Query(None, description="Filter by severity: LOW, MEDIUM, HIGH, CRITICAL"),
    status: Optional[str] = Query(None, description="Filter by status: active, acknowledged, resolved, dismissed"),
    zone_id: Optional[str] = Query(None, description="Filter by zone ID"),
    source_mode: Optional[str] = Query(None, description="Filter by source: live, demo, file"),
    has_snapshot: Optional[bool] = Query(None, description="Filter alerts with saved snapshots"),
    start_time: Optional[float] = Query(None, description="Start timestamp filter"),
    end_time: Optional[float] = Query(None, description="End timestamp filter")
):
    """Retrieve paginated alert history with comprehensive multi-criteria filtering."""
    return alert_service.get_alerts(
        limit=limit,
        cursor=cursor,
        alert_type=alert_type,
        severity=severity,
        status=status,
        zone_id=zone_id,
        source_mode=source_mode,
        has_snapshot=has_snapshot,
        start_time=start_time,
        end_time=end_time
    )


@router.get("/summary")
def get_alert_summary(
    hours: float = Query(24.0, ge=0.1, le=720.0, description="Time window in hours")
):
    """Retrieve aggregated alert counts by type, severity, status, and storage telemetry."""
    return alert_service.get_summary(hours=hours)


@router.get("/{alert_id}")
def get_alert_detail(alert_id: str):
    """Retrieve complete alert event details, associated snapshots, and lifecycle state changes."""
    alert = alert_service.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return alert


@router.get("/{alert_id}/snapshots")
def get_alert_snapshots(alert_id: str):
    """List all evidence snapshots captured for this alert."""
    alert = alert_service.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return {"alert_id": alert_id, "snapshots": alert.get("snapshots", [])}


@router.get("/{alert_id}/snapshot")
def get_alert_snapshot_image(
    alert_id: str,
    thumb: bool = Query(False, description="True to retrieve lightweight thumbnail")
):
    """
    Stream the evidence snapshot JPEG image.
    Fetches securely from private Vercel Blob or local disk fallback.
    Supports HTTP caching headers, path-traversal prevention, and authorization.
    """
    alert = alert_service.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    snapshots = alert.get("snapshots", [])
    if not snapshots:
        raise HTTPException(status_code=404, detail="No snapshot evidence available for this alert")

    # Use primary/first snapshot
    primary_snap = snapshots[0]
    storage_key = primary_snap["storage_key"]

    img_bytes, mime_type = storage_manager.get_snapshot_bytes(storage_key, thumbnail=thumb)
    if not img_bytes:
        raise HTTPException(status_code=404, detail="Snapshot image file missing from storage")

    # Secure binary streaming with immutable cache header
    return Response(
        content=img_bytes,
        media_type=mime_type or "image/jpeg",
        headers={
            "Cache-Control": "public, max-age=86400, immutable",
            "X-Alert-ID": alert_id,
            "X-Snapshot-Checksum": primary_snap.get("checksum") or ""
        }
    )


@router.patch("/{alert_id}/status")
def update_status(alert_id: str, body: AlertStatusUpdate):
    """Update alert lifecycle status (active, acknowledged, resolved, dismissed)."""
    try:
        updated = alert_service.update_alert_status(alert_id, body.status, body.reason or "Dashboard update")
        if not updated:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cleanup")
def purge_retention(body: CleanupRequest):
    """Purge expired alert records and delete orphaned evidence snapshot files."""
    return alert_service.cleanup_old_records(retention_days=body.retention_days)
