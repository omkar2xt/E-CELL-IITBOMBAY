# tests/test_zone_analytics.py
# StorePulse AI — Automated Unit Tests for Zone Analytics Engine
# Developer: Omkar Gurav

import pytest
import time
from backend.zone_analytics import Zone, ZoneAnalyticsEngine, DwellRecord


@pytest.fixture
def engine():
    eng = ZoneAnalyticsEngine()
    eng.set_zones([
        Zone(
            id="zone_entrance",
            name="Store Entrance",
            type="entrance",
            polygon=[(0.0, 0.0), (0.4, 0.0), (0.4, 0.5), (0.0, 0.5)],
            capacity=5,
            dwell_alert_seconds=30.0,
        ),
        Zone(
            id="zone_checkout",
            name="Checkout Counter",
            type="checkout",
            polygon=[(0.6, 0.6), (1.0, 0.6), (1.0, 1.0), (0.6, 1.0)],
            capacity=3,
            dwell_alert_seconds=60.0,
        ),
    ])
    return eng


class MockTrackedPerson:
    def __init__(self, track_id: int, bottom_center: tuple[int, int]):
        self.track_id = track_id
        self.bottom_center = bottom_center


def test_zone_point_in_polygon():
    zone = Zone(
        id="test_zone",
        name="Test",
        type="display",
        polygon=[(0.1, 0.1), (0.5, 0.1), (0.5, 0.5), (0.1, 0.5)],
        capacity=5,
    )
    # Inside
    assert zone.contains_point(0.2, 0.2) is True
    assert zone.contains_point(0.4, 0.4) is True
    # Outside
    assert zone.contains_point(0.0, 0.0) is False
    assert zone.contains_point(0.6, 0.6) is False
    assert zone.contains_point(0.2, 0.8) is False


def test_zone_entry_and_occupancy(engine):
    # Frame with 1 person inside zone_entrance (normalized x=0.2, y=0.2 -> 200, 200 on 1000x1000)
    p1 = MockTrackedPerson(1, (200, 200))
    engine.update([p1], frame_w=1000, frame_h=1000)

    stats = engine.get_zone_stats()
    entrance_stats = stats["zone_entrance"]
    assert entrance_stats["current_occupancy"] == 1
    assert entrance_stats["total_entries"] == 1


def test_continuous_presence_no_duplicate_entry(engine):
    p1 = MockTrackedPerson(1, (200, 200))
    # Update over 5 consecutive frames
    for _ in range(5):
        engine.update([p1], frame_w=1000, frame_h=1000)

    stats = engine.get_zone_stats()
    entrance_stats = stats["zone_entrance"]
    # Total entries must remain 1, not increment per frame!
    assert entrance_stats["total_entries"] == 1
    assert entrance_stats["current_occupancy"] == 1


def test_zone_transition_and_exit(engine):
    # Start at entrance
    p1 = MockTrackedPerson(1, (200, 200))
    engine.update([p1], frame_w=1000, frame_h=1000)

    # Move to checkout (800, 800)
    p1_moved = MockTrackedPerson(1, (800, 800))
    engine.update([p1_moved], frame_w=1000, frame_h=1000)

    stats = engine.get_zone_stats()
    assert stats["zone_entrance"]["current_occupancy"] == 0
    assert stats["zone_checkout"]["current_occupancy"] == 1
    assert stats["zone_checkout"]["total_entries"] == 1

    # Check transitions
    transitions_data = engine.get_transitions()
    transitions = transitions_data.get("transitions", [])
    assert any(
        t.get("from_zone") == "zone_entrance"
        and t.get("to_zone") == "zone_checkout"
        and t.get("count") == 1
        for t in transitions
    )


def test_dwell_time_calculation(engine):
    p1 = MockTrackedPerson(1, (200, 200))
    engine.update([p1], frame_w=1000, frame_h=1000)

    # Person leaves
    p1_exit = MockTrackedPerson(1, (500, 100))  # outside both zones
    engine.update([p1_exit], frame_w=1000, frame_h=1000)

    stats = engine.get_zone_stats()
    assert stats["zone_entrance"]["current_occupancy"] == 0
    # Dwell recorded
    assert stats["zone_entrance"]["total_entries"] == 1
    assert "avg_dwell_seconds" in stats["zone_entrance"]


def test_capacity_congestion_alert(engine):
    # Add people exceeding capacity (capacity=3 for checkout)
    people = [
        MockTrackedPerson(10, (800, 800)),
        MockTrackedPerson(11, (850, 850)),
        MockTrackedPerson(12, (900, 900)),
        MockTrackedPerson(13, (750, 750)),
    ]
    engine.update(people, frame_w=1000, frame_h=1000)

    stats = engine.get_zone_stats()
    checkout = stats["zone_checkout"]
    assert checkout["current_occupancy"] == 4
    assert checkout["congestion_level"] in ("HIGH", "CRITICAL")
