# StorePulse AI — Database Models
# Developer: Omkar Gurav
# Hierarchical schema: Store -> Zones, Processing Sessions, Alerts, Evidence Snapshots, Audit

import time
import uuid
from typing import Dict, Any, Optional
from sqlalchemy import (
    Column, String, Integer, Float, Text, ForeignKey,
    Index, Boolean, DateTime
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Store(Base):
    """Retail Store / Site."""
    __tablename__ = "stores"

    id = Column(String(64), primary_key=True, default="store-01")
    name = Column(String(128), nullable=False, default="StorePulse Flagship Store #1")
    created_at = Column(Float, default=time.time)

    # Relationships
    zones = relationship("ZoneModel", back_populates="store", cascade="all, delete-orphan")
    alerts = relationship("AlertEvent", back_populates="store")


class ZoneModel(Base):
    """Store Zones configured for CV analytics."""
    __tablename__ = "zones"

    id = Column(String(64), primary_key=True)
    store_id = Column(String(64), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, default="store-01")
    name = Column(String(128), nullable=False)
    zone_type = Column(String(64), nullable=False)  # entrance, checkout, electronics, grocery, promo
    configuration = Column(Text, nullable=True)     # JSON polygon coordinates
    capacity = Column(Integer, default=10)
    dwell_alert_seconds = Column(Float, default=120.0)
    created_at = Column(Float, default=time.time)

    # Relationships
    store = relationship("Store", back_populates="zones")
    alerts = relationship("AlertEvent", back_populates="zone")


class ProcessingSession(Base):
    """Video processing execution session."""
    __tablename__ = "processing_sessions"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_type = Column(String(32), nullable=False)  # file, webcam, stream, demo
    source_path = Column(String(256), nullable=True)
    started_at = Column(Float, default=time.time)
    ended_at = Column(Float, nullable=True)
    status = Column(String(32), default="active")     # active, stopped, error
    frames_processed = Column(Integer, default=0)

    # Relationships
    alerts = relationship("AlertEvent", back_populates="session")


class AlertEvent(Base):
    """
    Central Alert Event record.
    Tracks threshold violations, queue spikes, bottlenecks, and dwell alerts.
    """
    __tablename__ = "alert_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    fingerprint = Column(String(128), nullable=False, index=True)
    alert_type = Column(String(64), nullable=False, index=True)  # queue_threshold, excessive_dwell, bottleneck, friction, capacity
    severity = Column(String(16), nullable=False, default="MEDIUM", index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(32), nullable=False, default="active", index=True)    # active, acknowledged, resolved, dismissed
    
    store_id = Column(String(64), ForeignKey("stores.id", ondelete="SET NULL"), nullable=True)
    zone_id = Column(String(64), ForeignKey("zones.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id = Column(String(64), ForeignKey("processing_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    
    metric_name = Column(String(64), nullable=False)        # e.g. "queue_count", "dwell_time", "flow_friction"
    metric_value = Column(Float, nullable=False)
    threshold_value = Column(Float, nullable=False)
    source_mode = Column(String(32), nullable=False, default="demo", index=True)  # live, demo, file
    
    triggered_at = Column(Float, nullable=False, default=time.time, index=True)
    resolved_at = Column(Float, nullable=True)
    snapshot_status = Column(String(32), default="none", index=True)  # none, pending, saved, failed
    
    message = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)  # Evidence context (e.g. track IDs, bbox info)

    # Relationships
    store = relationship("Store", back_populates="alerts")
    zone = relationship("ZoneModel", back_populates="alerts")
    session = relationship("ProcessingSession", back_populates="alerts")
    snapshots = relationship("EvidenceSnapshot", back_populates="alert", cascade="all, delete-orphan")
    state_changes = relationship("AlertStateChange", back_populates="alert", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_alert_status_time", "status", "triggered_at"),
        Index("idx_alert_type_time", "alert_type", "triggered_at"),
        Index("idx_alert_zone_time", "zone_id", "triggered_at"),
        Index("idx_alert_session_time", "session_id", "triggered_at"),
        Index("idx_alert_fingerprint_status", "fingerprint", "status"),
    )


class EvidenceSnapshot(Base):
    """
    Image evidence associated with an alert event.
    Stores metadata only; raw image binary is stored in persistent local evidence directory.
    """
    __tablename__ = "evidence_snapshots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(String(36), ForeignKey("alert_events.id", ondelete="CASCADE"), nullable=False, index=True)
    
    storage_key = Column(String(256), nullable=False)     # Relative path inside snapshots/
    thumbnail_key = Column(String(256), nullable=True)   # Relative thumbnail path
    mime_type = Column(String(32), default="image/jpeg")
    file_size_bytes = Column(Integer, default=0)
    image_width = Column(Integer, default=0)
    image_height = Column(Integer, default=0)
    checksum = Column(String(64), nullable=True)         # SHA-256 hash of file contents
    capture_status = Column(String(32), default="saved")  # saved, failed
    created_at = Column(Float, default=time.time, index=True)

    # Relationship
    alert = relationship("AlertEvent", back_populates="snapshots")


class AlertStateChange(Base):
    """Audit log of status updates for an alert event (e.g. active -> acknowledged)."""
    __tablename__ = "alert_state_changes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(36), ForeignKey("alert_events.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_status = Column(String(32), nullable=False)
    new_status = Column(String(32), nullable=False)
    changed_at = Column(Float, default=time.time, index=True)
    reason = Column(Text, nullable=True)

    # Relationship
    alert = relationship("AlertEvent", back_populates="state_changes")


class AuditLog(Base):
    """System-level audit and processing log."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(64), nullable=False, index=True)
    description = Column(Text, nullable=False)
    timestamp = Column(Float, default=time.time, index=True)
    details_json = Column(Text, nullable=True)
