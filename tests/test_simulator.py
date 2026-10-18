# tests/test_simulator.py
# StorePulse AI — Automated Unit Tests for What-If Layout Simulator
# Developer: Omkar Gurav

import pytest
from backend.simulator import (
    LayoutConfig,
    ShelfElement,
    layout_store,
    layout_simulator,
)


def test_layout_store_crud():
    layout = LayoutConfig(
        id="test_layout_1",
        name="Test Layout 1",
        description="A unit test layout",
        elements=[
            ShelfElement(
                id="shelf_1",
                element_type="shelf",
                x=100.0,
                y=100.0,
                width=80.0,
                height=40.0,
                rotation=0.0,
                label="Center Aisle Shelf",
            )
        ],
        zones=[{"id": "zone_a", "name": "Zone A", "type": "display"}],
        is_baseline=False,
    )
    # Save
    saved = layout_store.save_layout(layout)
    assert saved.id == "test_layout_1"

    # Get
    retrieved = layout_store.get_layout("test_layout_1")
    assert retrieved is not None
    assert retrieved.name == "Test Layout 1"
    assert len(retrieved.elements) == 1

    # List
    all_layouts = layout_store.list_layouts()
    assert any(l["id"] == "test_layout_1" for l in all_layouts)

    # Delete
    deleted = layout_store.delete_layout("test_layout_1")
    assert deleted is True
    assert layout_store.get_layout("test_layout_1") is None


def test_baseline_preservation():
    baseline = layout_store.get_baseline()
    assert baseline is not None
    assert baseline.is_baseline is True

    # Baseline cannot be deleted
    cannot_delete = layout_store.delete_layout(baseline.id)
    assert cannot_delete is False
    # Baseline still exists
    assert layout_store.get_layout(baseline.id) is not None


def test_simulator_heuristic_calculation():
    baseline = layout_store.get_baseline()
    assert baseline is not None

    # Create proposed layout with additional shelf blocking flow
    proposed = LayoutConfig(
        id="test_proposed",
        name="Proposed Crowded Layout",
        description="Layout with more obstacles",
        elements=baseline.elements + [
            ShelfElement(
                id="extra_shelf_1",
                element_type="obstacle",
                x=400.0,
                y=300.0,
                width=120.0,
                height=60.0,
                rotation=0.0,
                label="Promotional Island",
            )
        ],
        zones=baseline.zones,
        is_baseline=False,
    )

    result = layout_simulator.simulate(baseline, proposed)

    assert "comparison" in result
    assert "baseline" in result
    assert "proposed" in result
    assert "assumptions" in result
    assert len(result["comparison"]) >= 5

    # Check baseline and proposed metrics
    b_metrics = result["baseline"]["metrics"]
    p_metrics = result["proposed"]["metrics"]
    for key in [
        "space_utilization_pct",
        "free_space_pct",
        "avg_weighted_walking_distance",
        "checkout_distance",
        "route_conflict_score",
    ]:
        assert key in b_metrics
        assert key in p_metrics

    # Check comparison rows structure
    for row in result["comparison"]:
        assert "metric" in row
        assert "baseline" in row
        assert "proposed" in row
        assert "direction" in row
        assert "source" in row

    # Assumptions must declare heuristic nature and limitations
    assert len(result["assumptions"]) > 0
