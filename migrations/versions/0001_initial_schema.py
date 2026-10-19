"""0001_initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-19 23:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. stores
    op.create_table(
        'stores',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. zones
    op.create_table(
        'zones',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('store_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('zone_type', sa.String(length=64), nullable=False),
        sa.Column('configuration', sa.Text(), nullable=True),
        sa.Column('capacity', sa.Integer(), nullable=True),
        sa.Column('dwell_alert_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. processing_sessions
    op.create_table(
        'processing_sessions',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('source_type', sa.String(length=32), nullable=False),
        sa.Column('source_path', sa.String(length=256), nullable=True),
        sa.Column('started_at', sa.Float(), nullable=True),
        sa.Column('ended_at', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.Column('frames_processed', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. alert_events
    op.create_table(
        'alert_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('fingerprint', sa.String(length=128), nullable=False),
        sa.Column('alert_type', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('store_id', sa.String(length=64), nullable=True),
        sa.Column('zone_id', sa.String(length=64), nullable=True),
        sa.Column('session_id', sa.String(length=64), nullable=True),
        sa.Column('metric_name', sa.String(length=64), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('threshold_value', sa.Float(), nullable=False),
        sa.Column('source_mode', sa.String(length=32), nullable=False),
        sa.Column('triggered_at', sa.Float(), nullable=False),
        sa.Column('resolved_at', sa.Float(), nullable=True),
        sa.Column('snapshot_status', sa.String(length=32), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['processing_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_events_alert_type'), 'alert_events', ['alert_type'], unique=False)
    op.create_index(op.f('ix_alert_events_fingerprint'), 'alert_events', ['fingerprint'], unique=False)
    op.create_index(op.f('ix_alert_events_session_id'), 'alert_events', ['session_id'], unique=False)
    op.create_index(op.f('ix_alert_events_severity'), 'alert_events', ['severity'], unique=False)
    op.create_index(op.f('ix_alert_events_snapshot_status'), 'alert_events', ['snapshot_status'], unique=False)
    op.create_index(op.f('ix_alert_events_source_mode'), 'alert_events', ['source_mode'], unique=False)
    op.create_index(op.f('ix_alert_events_status'), 'alert_events', ['status'], unique=False)
    op.create_index(op.f('ix_alert_events_triggered_at'), 'alert_events', ['triggered_at'], unique=False)
    op.create_index(op.f('ix_alert_events_zone_id'), 'alert_events', ['zone_id'], unique=False)

    op.create_index('idx_alert_fingerprint_status', 'alert_events', ['fingerprint', 'status'], unique=False)
    op.create_index('idx_alert_session_time', 'alert_events', ['session_id', 'triggered_at'], unique=False)
    op.create_index('idx_alert_status_time', 'alert_events', ['status', 'triggered_at'], unique=False)
    op.create_index('idx_alert_type_time', 'alert_events', ['alert_type', 'triggered_at'], unique=False)
    op.create_index('idx_alert_zone_time', 'alert_events', ['zone_id', 'triggered_at'], unique=False)

    # 5. evidence_snapshots
    op.create_table(
        'evidence_snapshots',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('alert_id', sa.String(length=36), nullable=False),
        sa.Column('storage_key', sa.String(length=256), nullable=False),
        sa.Column('thumbnail_key', sa.String(length=256), nullable=True),
        sa.Column('mime_type', sa.String(length=32), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('image_width', sa.Integer(), nullable=True),
        sa.Column('image_height', sa.Integer(), nullable=True),
        sa.Column('checksum', sa.String(length=64), nullable=True),
        sa.Column('capture_status', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['alert_id'], ['alert_events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evidence_snapshots_alert_id'), 'evidence_snapshots', ['alert_id'], unique=False)
    op.create_index(op.f('ix_evidence_snapshots_created_at'), 'evidence_snapshots', ['created_at'], unique=False)

    # 6. alert_state_changes
    op.create_table(
        'alert_state_changes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alert_id', sa.String(length=36), nullable=False),
        sa.Column('previous_status', sa.String(length=32), nullable=False),
        sa.Column('new_status', sa.String(length=32), nullable=False),
        sa.Column('changed_at', sa.Float(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['alert_id'], ['alert_events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_state_changes_alert_id'), 'alert_state_changes', ['alert_id'], unique=False)
    op.create_index(op.f('ix_alert_state_changes_changed_at'), 'alert_state_changes', ['changed_at'], unique=False)

    # 7. audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.Float(), nullable=True),
        sa.Column('details_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_event_type'), 'audit_logs', ['event_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('alert_state_changes')
    op.drop_table('evidence_snapshots')
    op.drop_table('alert_events')
    op.drop_table('processing_sessions')
    op.drop_table('zones')
    op.drop_table('stores')
