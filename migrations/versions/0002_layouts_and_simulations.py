"""0002_layouts_and_simulations

Revision ID: 0002_layouts_and_simulations
Revises: 0001_initial_schema
Create Date: 2026-10-20 00:28:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_layouts_and_simulations'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. layouts table
    op.create_table(
        'layouts',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_baseline', sa.Boolean(), nullable=True),
        sa.Column('elements_json', sa.Text(), nullable=False),
        sa.Column('zones_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_layouts_created_at'), 'layouts', ['created_at'], unique=False)
    op.create_index(op.f('ix_layouts_is_baseline'), 'layouts', ['is_baseline'], unique=False)

    # 2. simulation_results table
    op.create_table(
        'simulation_results',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('baseline_id', sa.String(length=64), nullable=False),
        sa.Column('proposed_id', sa.String(length=64), nullable=False),
        sa.Column('is_synthetic', sa.Boolean(), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('walking_distance_change_pct', sa.Float(), nullable=False),
        sa.Column('conflict_score', sa.Float(), nullable=False),
        sa.Column('bottleneck_risk_score', sa.Float(), nullable=False),
        sa.Column('space_utilization_score', sa.Float(), nullable=False),
        sa.Column('flow_friction_index', sa.Float(), nullable=False),
        sa.Column('zone_metrics_json', sa.Text(), nullable=True),
        sa.Column('details_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_simulation_results_baseline_id'), 'simulation_results', ['baseline_id'], unique=False)
    op.create_index(op.f('ix_simulation_results_created_at'), 'simulation_results', ['created_at'], unique=False)
    op.create_index(op.f('ix_simulation_results_is_synthetic'), 'simulation_results', ['is_synthetic'], unique=False)
    op.create_index(op.f('ix_simulation_results_proposed_id'), 'simulation_results', ['proposed_id'], unique=False)

    # 3. analytics_snapshots table
    op.create_table(
        'analytics_snapshots',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('store_id', sa.String(length=64), nullable=True),
        sa.Column('total_in', sa.Integer(), nullable=True),
        sa.Column('total_out', sa.Integer(), nullable=True),
        sa.Column('current_occupancy', sa.Integer(), nullable=True),
        sa.Column('flow_friction_score', sa.Float(), nullable=True),
        sa.Column('active_dwell_time_avg', sa.Float(), nullable=True),
        sa.Column('zones_data_json', sa.Text(), nullable=True),
        sa.Column('is_demo', sa.Boolean(), nullable=True),
        sa.Column('recorded_at', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analytics_snapshots_is_demo'), 'analytics_snapshots', ['is_demo'], unique=False)
    op.create_index(op.f('ix_analytics_snapshots_recorded_at'), 'analytics_snapshots', ['recorded_at'], unique=False)
    op.create_index(op.f('ix_analytics_snapshots_store_id'), 'analytics_snapshots', ['store_id'], unique=False)


def downgrade() -> None:
    op.drop_table('analytics_snapshots')
    op.drop_table('simulation_results')
    op.drop_table('layouts')
