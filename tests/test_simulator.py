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


# ==============================================================================
# PHASE 4 — WHAT-IF SIMULATOR & TRANSITION MATRIX TESTS
# ==============================================================================


class MockPerson:
    def __init__(self, track_id: int, bottom_center: tuple):
        self.track_id = track_id
        self.bottom_center = bottom_center


def test_transition_matrix_counts_and_probabilities():
    """Requirement 1: Verify origin -> destination transition counts and normalized probabilities."""
    from backend.zone_analytics import ZoneAnalyticsEngine, Zone

    eng = ZoneAnalyticsEngine()
    eng.set_zones([
        Zone(id="z_in", name="Entrance", type="entrance",
             polygon=[(0.0, 0.0), (0.3, 0.0), (0.3, 0.5), (0.0, 0.5)], capacity=5),
        Zone(id="z_groc", name="Grocery", type="browsing",
             polygon=[(0.4, 0.0), (0.7, 0.0), (0.7, 0.5), (0.4, 0.5)], capacity=5),
        Zone(id="z_out", name="Checkout", type="checkout",
             polygon=[(0.7, 0.5), (1.0, 0.5), (1.0, 1.0), (0.7, 1.0)], capacity=3),
    ])

    t = 1000.0
    # Person 1 goes: Entrance (150, 200) -> Grocery (550, 200) -> Checkout (850, 750)
    p1 = MockPerson(1, (150, 200))
    eng.update([p1], frame_w=1000, frame_h=1000, timestamp=t)

    p1_groc = MockPerson(1, (550, 200))
    eng.update([p1_groc], frame_w=1000, frame_h=1000, timestamp=t + 1.0)

    p1_out = MockPerson(1, (850, 750))
    eng.update([p1_out], frame_w=1000, frame_h=1000, timestamp=t + 2.0)

    # Person 2 goes: Entrance -> Grocery -> back to Entrance
    p2 = MockPerson(2, (150, 200))
    eng.update([p2], frame_w=1000, frame_h=1000, timestamp=t + 3.0)

    p2_groc = MockPerson(2, (550, 200))
    eng.update([p2_groc], frame_w=1000, frame_h=1000, timestamp=t + 4.0)

    p2_back = MockPerson(2, (150, 200))
    eng.update([p2_back], frame_w=1000, frame_h=1000, timestamp=t + 5.0)

    data = eng.get_transitions()
    transitions = data["transitions"]

    # (z_in -> z_groc) has count 2
    in_to_groc = next(t for t in transitions if t["from_zone"] == "z_in" and t["to_zone"] == "z_groc")
    assert in_to_groc["count"] == 2
    # All exits from z_in went to z_groc, so probability = 1.0
    assert in_to_groc["probability"] == 1.0

    # From z_groc: 1 went to Checkout (0.5), 1 went to Entrance (0.5)
    groc_to_out = next(t for t in transitions if t["from_zone"] == "z_groc" and t["to_zone"] == "z_out")
    assert groc_to_out["count"] == 1
    assert groc_to_out["probability"] == 0.5

    groc_to_in = next(t for t in transitions if t["from_zone"] == "z_groc" and t["to_zone"] == "z_in")
    assert groc_to_in["count"] == 1
    assert groc_to_in["probability"] == 0.5

    assert data["total_transitions"] == 4
    assert data["matrix"]["z_in"]["z_groc"]["count"] == 2
    assert data["matrix"]["z_groc"]["z_out"]["count"] == 1


def test_repeated_frame_no_duplicate_transitions():
    """Requirement 2: Repeated frames inside the same zone do not create transitions."""
    from backend.zone_analytics import ZoneAnalyticsEngine, Zone

    eng = ZoneAnalyticsEngine()
    eng.set_zones([
        Zone(id="z1", name="Zone 1", type="browsing",
             polygon=[(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)], capacity=5)
    ])

    p = MockPerson(10, (200, 200))
    # Update for 10 frames
    for i in range(10):
        eng.update([p], frame_w=1000, frame_h=1000, timestamp=100.0 + i)

    data = eng.get_transitions()
    assert data["total_transitions"] == 0
    assert len(data["transitions"]) == 0


def test_empty_and_insufficient_transition_data():
    """Requirement 3: Explicitly flag insufficient or empty transition data."""
    from backend.zone_analytics import ZoneAnalyticsEngine

    eng = ZoneAnalyticsEngine()
    data = eng.get_transitions()

    assert data["total_transitions"] == 0
    assert data["data_sufficient"] is False
    assert data["confidence"] == "LOW"
    assert "transitions" in data
    assert isinstance(data["matrix"], dict)


def test_obstacle_and_geometry_validation():
    """Requirement 6: Obstacle overlap and store boundary validation."""
    # 1. Valid layout
    valid_layout = LayoutConfig(
        id="valid_l",
        name="Valid Layout",
        description="Clean layout",
        elements=[
            ShelfElement("e", "entrance", 0.0, 0.8, 0.1, 0.1),
            ShelfElement("c", "checkout", 0.8, 0.1, 0.1, 0.2),
            ShelfElement("s1", "shelf", 0.2, 0.2, 0.1, 0.3),
            ShelfElement("s2", "shelf", 0.5, 0.2, 0.1, 0.3),  # no overlap
        ]
    )
    res_valid = layout_simulator.validate_layout(valid_layout)
    assert res_valid["is_valid"] is True
    assert res_valid["overlap_count"] == 0

    # 2. Overlapping shelves (collision)
    overlap_layout = LayoutConfig(
        id="overlap_l",
        name="Overlapping Layout",
        description="Collision layout",
        elements=[
            ShelfElement("e", "entrance", 0.0, 0.8, 0.1, 0.1),
            ShelfElement("s1", "shelf", 0.3, 0.3, 0.2, 0.2),
            ShelfElement("s2", "shelf", 0.35, 0.35, 0.2, 0.2),  # overlapping s1!
        ]
    )
    res_overlap = layout_simulator.validate_layout(overlap_layout)
    assert res_overlap["overlap_count"] >= 1
    assert any("overlapping" in w.lower() for w in res_overlap["warnings"])
    assert res_overlap["overlap_pairs"][0]["element_1"] == "s1"
    assert res_overlap["overlap_pairs"][0]["element_2"] == "s2"


def test_zero_baseline_percentage_handling():
    """Requirement 8: Zero-baseline difference returns safe string without division by zero."""
    baseline = LayoutConfig(
        id="b_zero",
        name="Zero Baseline",
        description="Baseline with 0 conflicts",
        elements=[
            ShelfElement("e", "entrance", 0.1, 0.8, 0.1, 0.1),
            ShelfElement("c", "checkout", 0.8, 0.1, 0.1, 0.1),
        ],
        zones=[]
    )
    # Proposed adds overlapping elements -> conflict score > 0
    proposed = LayoutConfig(
        id="p_conflicts",
        name="Proposed Conflicts",
        description="Proposed with conflicts",
        elements=[
            ShelfElement("e", "entrance", 0.1, 0.8, 0.1, 0.1),
            ShelfElement("c", "checkout", 0.8, 0.1, 0.1, 0.1),
            ShelfElement("s1", "shelf", 0.4, 0.4, 0.2, 0.2),
            ShelfElement("s2", "shelf", 0.45, 0.45, 0.2, 0.2),
        ],
        zones=[]
    )

    result = layout_simulator.simulate(baseline, proposed)
    conflict_row = next(r for r in result["comparison"] if r["metric"] == "Route Conflict Score")

    assert conflict_row["baseline"] == "0.0"
    assert float(conflict_row["proposed"]) > 0.0
    # Must NOT throw ZeroDivisionError and must declare safe percentage
    assert "baseline is 0" in conflict_row["pct_diff"].lower() or conflict_row["pct_diff"] == "N/A"
    assert conflict_row["direction"] == "WORSE"


def test_distinction_between_observed_and_predicted_metrics():
    """Requirement 9: Strict distinction between measured camera data and simulated estimates."""
    baseline = layout_store.get_baseline()
    proposed = layout_store.get_baseline()

    mock_analytics = {
        "zone_entrance": {
            "zone_name": "Store Entrance",
            "avg_dwell_seconds": 34.5,
            "sample_count": 12,
            "congestion_level": "LOW",
        }
    }
    mock_transitions = {
        "data_sufficient": True,
        "transitions": [{"from_zone": "zone_entrance", "to_zone": "zone_checkout", "count": 10, "probability": 0.8}],
    }

    result = layout_simulator.simulate(
        baseline, proposed, baseline_analytics=mock_analytics, transition_data=mock_transitions
    )

    assert result["used_empirical_transitions"] is True

    # Check comparison table sources
    for row in result["comparison"]:
        if "[MEASURED]" in row["metric"]:
            assert row["source"] == "real_measurement"
            assert "physical trial" in row["proposed"].lower()
        else:
            assert row["source"] == "heuristic_estimate"
            assert row["confidence"] in ("MEDIUM", "LOW")

    # Zone comparisons must show aisle clearance and predicted risk
    assert "zone_comparisons" in result
    assert isinstance(result["zone_comparisons"], list)

