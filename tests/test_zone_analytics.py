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


# ==============================================================================
# PHASE 3 — DWELL-TIME & BOTTLENECK SIMULATED UNIT TESTS
# Note: These are controlled deterministic unit tests with simulated tracks.
# ==============================================================================


def test_zone_entry_and_exit_with_grace_period():
    """Requirement 1: Verify entry and finalized exit via grace period hysteresis."""
    eng = ZoneAnalyticsEngine(exit_grace_seconds=2.0)
    eng.set_zones([
        Zone(id="z_disp", name="Display Area", type="display",
             polygon=[(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)], capacity=2)
    ])

    t0 = 1000.0
    p1 = MockTrackedPerson(10, (200, 200))

    # Frame 1: Person enters at t0
    eng.update([p1], frame_w=1000, frame_h=1000, timestamp=t0)
    stats = eng.get_zone_stats(current_time=t0)["z_disp"]
    assert stats["current_occupancy"] == 1
    assert stats["total_entries"] == 1
    assert stats["total_completed_visits"] == 0

    # Frame 2: Person steps outside at t0 + 1.0 (inside 2.0s grace period)
    p1_out = MockTrackedPerson(10, (800, 800))
    eng.update([p1_out], frame_w=1000, frame_h=1000, timestamp=t0 + 1.0)
    stats = eng.get_zone_stats(current_time=t0 + 1.0)["z_disp"]
    assert stats["current_occupancy"] == 0
    assert stats["total_completed_visits"] == 0  # not finalized yet!

    # Frame 3: Outside after grace period expires (t0 + 3.5s)
    eng.update([p1_out], frame_w=1000, frame_h=1000, timestamp=t0 + 3.5)
    stats = eng.get_zone_stats(current_time=t0 + 3.5)["z_disp"]
    assert stats["current_occupancy"] == 0
    assert stats["total_completed_visits"] == 1
    # Duration was measured up to candidate exit time (1.0s elapsed)
    assert stats["avg_dwell_seconds"] == 1.0


def test_dwell_time_elapsed_timestamps():
    """Requirement 2: Dwell time uses elapsed timestamps, not fixed FPS assumptions."""
    eng = ZoneAnalyticsEngine(exit_grace_seconds=1.0)
    eng.set_zones([
        Zone(id="z_aisle", name="Aisle 1", type="browsing",
             polygon=[(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)], capacity=5)
    ])

    t0 = 100.0
    p = MockTrackedPerson(5, (250, 250))

    # Enter at t0
    eng.update([p], frame_w=1000, frame_h=1000, timestamp=t0)

    # Frame 2 happens 18.7 seconds later (irregular video/stream interval)
    eng.update([p], frame_w=1000, frame_h=1000, timestamp=t0 + 18.7)
    stats = eng.get_zone_stats(current_time=t0 + 18.7)["z_aisle"]
    # Real-time active dwell should reflect exactly 18.7s
    assert stats["active_avg_dwell_seconds"] == 18.7

    # Person exits at t0 + 25.0
    p_out = MockTrackedPerson(5, (900, 900))
    eng.update([p_out], frame_w=1000, frame_h=1000, timestamp=t0 + 25.0)
    # Finalize after grace
    eng.update([p_out], frame_w=1000, frame_h=1000, timestamp=t0 + 27.0)

    stats = eng.get_zone_stats(current_time=t0 + 27.0)["z_aisle"]
    assert stats["total_completed_visits"] == 1
    assert stats["avg_dwell_seconds"] == 25.0

    # Negative timestamp guard: simulate video rewind to t0 = 50.0
    rec = DwellRecord(track_id=99, zone_id="z_aisle", enter_time=100.0)
    assert rec.dwell_seconds(now=50.0) == 0.0


def test_multiple_people_same_zone():
    """Requirement 3: Multiple people visiting the same zone concurrently."""
    eng = ZoneAnalyticsEngine()
    eng.set_zones([
        Zone(id="z_queue", name="Queue", type="queue",
             polygon=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)], capacity=10)
    ])

    t0 = 200.0
    people = [
        MockTrackedPerson(101, (200, 200)),
        MockTrackedPerson(102, (300, 300)),
        MockTrackedPerson(103, (400, 400)),
    ]
    eng.update(people, frame_w=1000, frame_h=1000, timestamp=t0)

    stats = eng.get_zone_stats(current_time=t0)["z_queue"]
    assert stats["current_occupancy"] == 3
    assert stats["unique_visitors"] == 3
    assert stats["total_entries"] == 3

    # One leaves, two stay
    remaining = [MockTrackedPerson(101, (200, 200)), MockTrackedPerson(102, (300, 300))]
    eng.update(remaining, frame_w=1000, frame_h=1000, timestamp=t0 + 5.0)

    stats = eng.get_zone_stats(current_time=t0 + 5.0)["z_queue"]
    assert stats["current_occupancy"] == 2
    assert stats["unique_visitors"] == 3


def test_repeated_boundary_crossings_hysteresis():
    """Requirement 4: Repeated boundary crossings do not duplicate visits."""
    eng = ZoneAnalyticsEngine(exit_grace_seconds=2.0)
    eng.set_zones([
        Zone(id="z_entry", name="Entrance", type="entrance",
             polygon=[(0.0, 0.0), (0.4, 0.0), (0.4, 0.4), (0.0, 0.4)], capacity=5)
    ])

    t0 = 300.0
    p_inside = MockTrackedPerson(42, (200, 200))
    p_border = MockTrackedPerson(42, (410, 200))  # just outside boundary

    # Inside
    eng.update([p_inside], frame_w=1000, frame_h=1000, timestamp=t0)
    # Jitter outside for 0.8s
    eng.update([p_border], frame_w=1000, frame_h=1000, timestamp=t0 + 0.8)
    # Jitter back inside at 1.5s (before 2.0s grace period expires)
    eng.update([p_inside], frame_w=1000, frame_h=1000, timestamp=t0 + 1.5)

    stats = eng.get_zone_stats(current_time=t0 + 1.5)["z_entry"]
    # Total entries must still be exactly 1!
    assert stats["total_entries"] == 1
    assert stats["current_occupancy"] == 1
    assert stats["total_completed_visits"] == 0


def test_interrupted_tracks_expiration():
    """Requirement 5: Temporary track interruption and track expiration handling."""
    eng = ZoneAnalyticsEngine(track_expire_seconds=4.0)
    eng.set_zones([
        Zone(id="z_browse", name="Browse", type="browsing",
             polygon=[(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)], capacity=5)
    ])

    t0 = 500.0
    p = MockTrackedPerson(77, (200, 200))

    # Person present at t0 and t0 + 2.0
    eng.update([p], frame_w=1000, frame_h=1000, timestamp=t0)
    eng.update([p], frame_w=1000, frame_h=1000, timestamp=t0 + 2.0)

    # Person disappears (tracking lost). Empty frame at t0 + 3.0 (< expire_seconds)
    eng.update([], frame_w=1000, frame_h=1000, timestamp=t0 + 3.0)
    stats = eng.get_zone_stats(current_time=t0 + 3.0)["z_browse"]
    # Occupancy is 0 since person is not in current frame
    assert stats["current_occupancy"] == 0

    # Frame at t0 + 7.0 (> 4.0s expiration elapsed since last seen at t0 + 2.0)
    eng.update([], frame_w=1000, frame_h=1000, timestamp=t0 + 7.0)
    stats = eng.get_zone_stats(current_time=t0 + 7.0)["z_browse"]
    assert stats["total_completed_visits"] == 1
    # Check that the record was finalized with interrupted flag
    assert eng._completed[0].interrupted is True


def test_long_dwell_threshold_alert():
    """Requirement 6: Configurable dwell alert threshold triggering."""
    eng = ZoneAnalyticsEngine()
    eng.set_zones([
        Zone(id="z_fast", name="Express Checkout", type="checkout",
             polygon=[(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)],
             capacity=5, dwell_alert_seconds=20.0)
    ])

    t0 = 600.0
    p1 = MockTrackedPerson(81, (200, 200))
    p2 = MockTrackedPerson(82, (300, 300))

    # Enter at t0
    eng.update([p1, p2], frame_w=1000, frame_h=1000, timestamp=t0)

    # 10s elapsed: no dwell alert
    eng.update([p1, p2], frame_w=1000, frame_h=1000, timestamp=t0 + 10.0)
    stats = eng.get_zone_stats(current_time=t0 + 10.0)["z_fast"]
    assert stats["dwell_alert"] is False
    assert stats["long_dwell_active_count"] == 0

    # 25s elapsed (> 20.0s threshold): both exceed threshold -> dwell alert triggers
    eng.update([p1, p2], frame_w=1000, frame_h=1000, timestamp=t0 + 25.0)
    stats = eng.get_zone_stats(current_time=t0 + 25.0)["z_fast"]
    assert stats["dwell_alert"] is True
    assert stats["long_dwell_active_count"] == 2


def test_sustained_congestion_vs_brief_crowding():
    """Requirement 7: Bottleneck persistence window prevents alert flickering."""
    eng = ZoneAnalyticsEngine(bottleneck_persistence_seconds=4.0)
    eng.set_zones([
        Zone(id="z_aisle", name="Snack Aisle", type="browsing",
             polygon=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
             capacity=2, congestion_threshold_ratio=1.0)
    ])

    t0 = 800.0
    crowd = [
        MockTrackedPerson(1, (100, 100)),
        MockTrackedPerson(2, (200, 200)),
        MockTrackedPerson(3, (300, 300)),  # 3 > capacity 2
    ]

    # Brief crowding (2.0s): exceeds capacity, but under persistence window (4.0s)
    eng.update(crowd, frame_w=1000, frame_h=1000, timestamp=t0)
    eng.update(crowd, frame_w=1000, frame_h=1000, timestamp=t0 + 2.0)

    stats = eng.get_zone_stats(current_time=t0 + 2.0)["z_aisle"]
    b = stats["bottleneck"]
    # Must NOT alert yet — prevents flickering
    assert b["is_bottleneck"] is False
    assert b["congested_duration_seconds"] == 2.0

    # Sustained congestion (5.0s > 4.0s window)
    eng.update(crowd, frame_w=1000, frame_h=1000, timestamp=t0 + 5.0)
    stats = eng.get_zone_stats(current_time=t0 + 5.0)["z_aisle"]
    b = stats["bottleneck"]
    assert b["is_bottleneck"] is True
    assert b["severity"] in ("HIGH", "CRITICAL")
    assert len(b["evidence"]) > 0
    assert "Snack Aisle" in b["recommendation"] or "capacity" in b["recommendation"].lower()

    # Congestion clears
    eng.update([MockTrackedPerson(1, (100, 100))], frame_w=1000, frame_h=1000, timestamp=t0 + 7.0)
    stats = eng.get_zone_stats(current_time=t0 + 7.0)["z_aisle"]
    assert stats["bottleneck"]["is_bottleneck"] is False


def test_missing_and_invalid_zone_configuration():
    """Requirement 9: Resilient handling of empty or degenerate zone definitions."""
    eng = ZoneAnalyticsEngine()
    # 1. No zones configured
    eng.set_zones([])
    eng.update([MockTrackedPerson(1, (500, 500))], frame_w=1000, frame_h=1000)
    assert eng.get_zone_stats() == {}
    assert eng.get_bottleneck_summary()["total_bottlenecks"] == 0

    # 2. Degenerate polygon (< 3 points)
    eng.set_zones([
        Zone(id="invalid_z", name="Invalid", type="display",
             polygon=[(0.1, 0.1), (0.2, 0.2)], capacity=5)
    ])
    eng.update([MockTrackedPerson(1, (150, 150))], frame_w=1000, frame_h=1000)
    stats = eng.get_zone_stats()
    assert "invalid_z" in stats
    assert stats["invalid_z"]["current_occupancy"] == 0

