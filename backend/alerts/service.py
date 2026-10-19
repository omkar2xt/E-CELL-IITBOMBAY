# StorePulse AI — Alert Management Service
# Developer: Omkar Gurav
# High-throughput asynchronous alert persistence, snapshot capture worker, and querying

import os
import time
import uuid
import json
import queue
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from backend.database.connection import get_db_context, SessionLocal
from backend.database.models import (
    AlertEvent, EvidenceSnapshot, AlertStateChange, AuditLog, ZoneModel
)
from backend.alerts.storage import storage_manager
from backend.alerts.deduplicator import deduplicator
from backend.ws_manager import manager
import asyncio

logger = logging.getLogger(__name__)


class AlertService:
    """
    Central orchestration service for alert lifecycle management.
    Implements a bounded worker queue for asynchronous non-blocking snapshot capture.
    """

    def __init__(self, queue_capacity: int = 100):
        self.queue_capacity = queue_capacity
        self._worker_queue = queue.Queue(maxsize=queue_capacity)
        self._is_running = True
        self._worker_thread = threading.Thread(target=self._process_snapshot_queue, daemon=True)
        self._worker_thread.start()
        print(f"[AlertService] Started asynchronous snapshot worker thread (queue capacity: {queue_capacity})")

    def _process_snapshot_queue(self):
        """Background worker thread processing snapshot compression and DB persistence."""
        while self._is_running:
            try:
                task = self._worker_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            alert_id = task["alert_id"]
            frame = task["frame"]

            try:
                # 1. Save snapshot image files (full + thumbnail)
                meta = storage_manager.save_snapshot(alert_id, frame)

                # 2. Persist EvidenceSnapshot record and update AlertEvent status
                with get_db_context() as db:
                    snapshot_record = EvidenceSnapshot(
                        id=str(uuid.uuid4()),
                        alert_id=alert_id,
                        storage_key=meta["storage_key"],
                        thumbnail_key=meta["thumbnail_key"],
                        mime_type="image/jpeg",
                        file_size_bytes=meta["file_size_bytes"],
                        image_width=meta["image_width"],
                        image_height=meta["image_height"],
                        checksum=meta["checksum"],
                        capture_status=meta["capture_status"],
                        created_at=time.time()
                    )
                    db.add(snapshot_record)

                    # Update parent alert status
                    alert = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
                    if alert:
                        alert.snapshot_status = "saved" if meta["capture_status"] == "saved" else "failed"

                # 3. Notify connected frontend clients via WebSocket
                self._broadcast_ws({
                    "type": "alert_snapshot_ready",
                    "alert_id": alert_id,
                    "snapshot": {
                        "storage_key": meta["storage_key"],
                        "thumbnail_key": meta["thumbnail_key"],
                        "file_size_bytes": meta["file_size_bytes"],
                        "checksum": meta["checksum"],
                        "status": meta["capture_status"]
                    }
                })

            except Exception as e:
                logger.error(f"[AlertService] Error saving snapshot for alert {alert_id}: {e}")
                with get_db_context() as db:
                    alert = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
                    if alert:
                        alert.snapshot_status = "failed"
            finally:
                self._worker_queue.task_done()

    def _broadcast_ws(self, payload: Dict[str, Any]):
        """Helper to broadcast JSON payload safely to WebSocket manager."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(manager.broadcast(payload), loop)
        except Exception:
            pass

    def trigger_alert(
        self,
        alert_type: str,
        severity: str,
        metric_name: str,
        metric_value: float,
        threshold_value: float,
        message: str,
        zone_id: Optional[str] = None,
        store_id: str = "store-01",
        session_id: Optional[str] = None,
        source_mode: str = "demo",
        metadata: Optional[Dict[str, Any]] = None,
        frame: Optional[np.ndarray] = None,
        cooldown_seconds: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Trigger an alert event.
        Enforces deduplication, records state transition, and queues snapshot asynchronously.
        """
        fingerprint = f"{alert_type}:{store_id}:{zone_id or 'global'}"

        should_trigger, existing_id = deduplicator.should_trigger(fingerprint, cooldown_seconds)
        if not should_trigger:
            return None  # Suppressed duplicate within active cooldown window

        alert_id = str(uuid.uuid4())
        now = time.time()
        has_frame = frame is not None and isinstance(frame, np.ndarray) and frame.size > 0
        snapshot_status = "pending" if has_frame else "none"

        # 1. Create database record atomically
        with get_db_context() as db:
            alert = AlertEvent(
                id=alert_id,
                fingerprint=fingerprint,
                alert_type=alert_type,
                severity=severity.upper(),
                status="active",
                store_id=store_id,
                zone_id=zone_id,
                session_id=session_id,
                metric_name=metric_name,
                metric_value=round(float(metric_value), 2),
                threshold_value=round(float(threshold_value), 2),
                source_mode=source_mode,
                triggered_at=now,
                snapshot_status=snapshot_status,
                message=message,
                metadata_json=json.dumps(metadata or {})
            )
            db.add(alert)

            # Record state transition
            change = AlertStateChange(
                alert_id=alert_id,
                previous_status="none",
                new_status="active",
                changed_at=now,
                reason=f"Alert triggered: {message}"
            )
            db.add(change)

        deduplicator.record_trigger(fingerprint, alert_id)

        # 2. Enqueue frame for async background capture (non-blocking)
        if has_frame:
            try:
                # Copy frame to isolate memory from video pipeline thread
                frame_copy = frame.copy()
                self._worker_queue.put_nowait({
                    "alert_id": alert_id,
                    "frame": frame_copy,
                    "metadata": metadata
                })
            except queue.Full:
                logger.warning(f"[AlertService] Snapshot queue full! Dropping snapshot for {alert_id}")
                with get_db_context() as db:
                    a = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
                    if a:
                        a.snapshot_status = "failed"

        # 3. Format response dictionary
        alert_dict = {
            "id": alert_id,
            "fingerprint": fingerprint,
            "alert_type": alert_type,
            "severity": severity.upper(),
            "status": "active",
            "store_id": store_id,
            "zone_id": zone_id,
            "metric_name": metric_name,
            "metric_value": round(float(metric_value), 2),
            "threshold_value": round(float(threshold_value), 2),
            "source_mode": source_mode,
            "triggered_at": now,
            "snapshot_status": snapshot_status,
            "message": message,
            "metadata": metadata or {}
        }

        # 4. Broadcast live notification to dashboard
        self._broadcast_ws({
            "type": "alert_triggered",
            "alert": alert_dict
        })

        return alert_dict

    def resolve_alert(self, alert_type: str, zone_id: Optional[str] = None, store_id: str = "store-01") -> Optional[str]:
        """Mark an active alert as resolved when condition returns below threshold."""
        fingerprint = f"{alert_type}:{store_id}:{zone_id or 'global'}"
        active_id = deduplicator.resolve(fingerprint)
        if not active_id:
            return None

        now = time.time()
        with get_db_context() as db:
            alert = db.query(AlertEvent).filter(AlertEvent.id == active_id).first()
            if alert and alert.status == "active":
                alert.status = "resolved"
                alert.resolved_at = now

                change = AlertStateChange(
                    alert_id=active_id,
                    previous_status="active",
                    new_status="resolved",
                    changed_at=now,
                    reason="Metric returned below threshold"
                )
                db.add(change)

        self._broadcast_ws({
            "type": "alert_resolved",
            "alert_id": active_id,
            "fingerprint": fingerprint,
            "resolved_at": now
        })
        return active_id

    def get_alerts(
        self,
        limit: int = 50,
        cursor: Optional[float] = None,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        zone_id: Optional[str] = None,
        source_mode: Optional[str] = None,
        has_snapshot: Optional[bool] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        High-performance paginated alert retrieval using keyset cursor pagination.
        """
        bounded_limit = min(max(1, limit), 100)
        db = SessionLocal()
        try:
            query = db.query(AlertEvent)

            if alert_type:
                query = query.filter(AlertEvent.alert_type == alert_type)
            if severity:
                query = query.filter(AlertEvent.severity == severity.upper())
            if status:
                query = query.filter(AlertEvent.status == status.lower())
            if zone_id:
                query = query.filter(AlertEvent.zone_id == zone_id)
            if source_mode:
                query = query.filter(AlertEvent.source_mode == source_mode)
            if has_snapshot is True:
                query = query.filter(AlertEvent.snapshot_status == "saved")
            elif has_snapshot is False:
                query = query.filter(AlertEvent.snapshot_status != "saved")
            if start_time is not None:
                query = query.filter(AlertEvent.triggered_at >= start_time)
            if end_time is not None:
                query = query.filter(AlertEvent.triggered_at <= end_time)

            # Keyset pagination cursor
            if cursor is not None:
                query = query.filter(AlertEvent.triggered_at < cursor)

            total_count = query.count()
            records = query.order_by(AlertEvent.triggered_at.desc(), AlertEvent.id.desc()).limit(bounded_limit).all()

            results = []
            for r in records:
                snapshots_list = [
                    {
                        "id": s.id,
                        "storage_key": s.storage_key,
                        "thumbnail_key": s.thumbnail_key,
                        "file_size_bytes": s.file_size_bytes,
                        "image_width": s.image_width,
                        "image_height": s.image_height,
                        "checksum": s.checksum,
                        "created_at": s.created_at
                    }
                    for s in r.snapshots
                ]
                results.append({
                    "id": r.id,
                    "fingerprint": r.fingerprint,
                    "alert_type": r.alert_type,
                    "severity": r.severity,
                    "status": r.status,
                    "store_id": r.store_id,
                    "zone_id": r.zone_id,
                    "session_id": r.session_id,
                    "metric_name": r.metric_name,
                    "metric_value": r.metric_value,
                    "threshold_value": r.threshold_value,
                    "source_mode": r.source_mode,
                    "triggered_at": r.triggered_at,
                    "resolved_at": r.resolved_at,
                    "snapshot_status": r.snapshot_status,
                    "message": r.message,
                    "metadata": json.loads(r.metadata_json) if r.metadata_json else {},
                    "snapshots": snapshots_list
                })

            next_cursor = records[-1].triggered_at if len(records) == bounded_limit else None

            return {
                "alerts": results,
                "count": len(results),
                "total": total_count,
                "next_cursor": next_cursor
            }
        finally:
            db.close()

    def get_alert_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve complete alert event details, snapshots, and state change history."""
        db = SessionLocal()
        try:
            alert = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
            if not alert:
                return None

            snapshots = [
                {
                    "id": s.id,
                    "storage_key": s.storage_key,
                    "thumbnail_key": s.thumbnail_key,
                    "file_size_bytes": s.file_size_bytes,
                    "image_width": s.image_width,
                    "image_height": s.image_height,
                    "checksum": s.checksum,
                    "created_at": s.created_at
                }
                for s in alert.snapshots
            ]

            state_changes = [
                {
                    "id": sc.id,
                    "previous_status": sc.previous_status,
                    "new_status": sc.new_status,
                    "changed_at": sc.changed_at,
                    "reason": sc.reason
                }
                for sc in alert.state_changes
            ]

            return {
                "id": alert.id,
                "fingerprint": alert.fingerprint,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "status": alert.status,
                "store_id": alert.store_id,
                "zone_id": alert.zone_id,
                "session_id": alert.session_id,
                "metric_name": alert.metric_name,
                "metric_value": alert.metric_value,
                "threshold_value": alert.threshold_value,
                "source_mode": alert.source_mode,
                "triggered_at": alert.triggered_at,
                "resolved_at": alert.resolved_at,
                "snapshot_status": alert.snapshot_status,
                "message": alert.message,
                "metadata": json.loads(alert.metadata_json) if alert.metadata_json else {},
                "snapshots": snapshots,
                "state_changes": sorted(state_changes, key=lambda x: x["changed_at"])
            }
        finally:
            db.close()

    def update_alert_status(self, alert_id: str, new_status: str, reason: str = "User manual update") -> Optional[Dict[str, Any]]:
        """Update lifecycle status of an alert (e.g. active -> acknowledged -> resolved)."""
        valid_statuses = {"active", "acknowledged", "resolved", "dismissed"}
        target = new_status.lower()
        if target not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")

        now = time.time()
        with get_db_context() as db:
            alert = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
            if not alert:
                return None

            prev = alert.status
            alert.status = target
            if target == "resolved" and not alert.resolved_at:
                alert.resolved_at = now

            change = AlertStateChange(
                alert_id=alert_id,
                previous_status=prev,
                new_status=target,
                changed_at=now,
                reason=reason
            )
            db.add(change)

        self._broadcast_ws({
            "type": "alert_status_updated",
            "alert_id": alert_id,
            "previous_status": prev,
            "new_status": target,
            "changed_at": now
        })

        return self.get_alert_by_id(alert_id)

    def get_summary(self, hours: float = 24.0) -> Dict[str, Any]:
        """Compute aggregated statistics of alert events."""
        db = SessionLocal()
        try:
            cutoff = time.time() - (hours * 3600.0)
            alerts = db.query(AlertEvent).filter(AlertEvent.triggered_at >= cutoff).all()

            by_severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            by_type = {}
            by_status = {"active": 0, "acknowledged": 0, "resolved": 0, "dismissed": 0}
            by_mode = {"live": 0, "demo": 0, "file": 0}

            for a in alerts:
                sev = a.severity.upper()
                if sev in by_severity:
                    by_severity[sev] += 1
                by_type[a.alert_type] = by_type.get(a.alert_type, 0) + 1
                st = a.status.lower()
                if st in by_status:
                    by_status[st] += 1
                by_mode[a.source_mode] = by_mode.get(a.source_mode, 0) + 1

            return {
                "time_window_hours": hours,
                "total_alerts": len(alerts),
                "active_alerts": by_status["active"],
                "by_severity": by_severity,
                "by_type": by_type,
                "by_status": by_status,
                "by_mode": by_mode,
                "storage": storage_manager.get_storage_stats()
            }
        finally:
            db.close()

    def cleanup_old_records(self, retention_days: int = 30) -> Dict[str, Any]:
        """Purge expired alerts and delete unreferenced snapshot files."""
        cutoff = time.time() - (retention_days * 86400.0)
        deleted_snapshots = 0
        deleted_alerts = 0

        with get_db_context() as db:
            expired_alerts = db.query(AlertEvent).filter(AlertEvent.triggered_at < cutoff).all()
            for a in expired_alerts:
                for s in a.snapshots:
                    storage_manager.delete_snapshot(s.storage_key, s.thumbnail_key)
                    deleted_snapshots += 1
                db.delete(a)
                deleted_alerts += 1

            audit = AuditLog(
                event_type="RETENTION_CLEANUP",
                description=f"Purged {deleted_alerts} alerts and {deleted_snapshots} snapshots older than {retention_days} days",
                timestamp=time.time(),
                details_json=json.dumps({"cutoff": cutoff, "retention_days": retention_days})
            )
            db.add(audit)

        return {
            "status": "success",
            "deleted_alerts": deleted_alerts,
            "deleted_snapshots": deleted_snapshots,
            "retention_days": retention_days
        }

# Global instance
alert_service = AlertService()
