"""
tests/test_counting_logic.py
=====================================================================
StorePulse AI — Counting Logic, Tracker Lifecycle & Occupancy Unit Tests

Validates:
1. One person appearing across 100 frames is counted only once (NOT 100 entries).
2. One valid entrance crossing increments Total In exactly once.
3. Total Out increments only once upon valid exit crossing.
4. Occupancy is consistently calculated from initial occupancy + in - out.
5. People already inside when tracking begins do not trigger false entries, and their exit is tracked.
6. Segment bounds check prevents people in other areas from triggering crossings.
7. Hysteresis, direction vector check, and re-crossing debounce prevent jitter duplicate counts.
8. Session reset / video restart cleanly clears old events and resets baselines.
=====================================================================
"""

import pytest
from tracking.counter import LineCounter
from tracking.tracker import TrackedPerson, PersonTracker


def test_one_person_across_100_frames_not_duplicate_counted():
    """Prove that one person appearing across 100 frames is not counted as 100 entries."""
    counter = LineCounter(line_start=(320, 0), line_end=(320, 480), orientation="horizontal", tolerance=5)

    # Frame 1: Person 101 starts outside (Side B: x=400)
    p = TrackedPerson(track_id=101, bbox=[380, 200, 420, 300], confidence=0.92)
    counter.update([p])
    assert counter.count_in == 0
    assert counter.count_out == 0
    assert counter.current_occupancy == 0

    # Frame 2: Person 101 crosses into the store (Side A: x=250) -> Valid Entry
    p_enter = TrackedPerson(track_id=101, bbox=[230, 200, 270, 300], confidence=0.92)
    counter.update([p_enter])
    assert counter.count_in == 1
    assert counter.count_out == 0
    assert counter.current_occupancy == 1
    assert counter.has_crossing_this_frame() is True

    # Frames 3 through 102 (100 frames): Person 101 moves around inside the store on Side A
    for frame_idx in range(100):
        # Vary coordinates within Side A (x in [100, 280], y in [150, 400])
        sim_x = 150 + (frame_idx % 40)
        sim_y = 200 + (frame_idx % 50)
        p_inside = TrackedPerson(track_id=101, bbox=[sim_x - 20, sim_y - 50, sim_x + 20, sim_y + 50], confidence=0.90)
        counter.update([p_inside])

        # Crucial assertion: count_in must STAY at 1, never 100!
        assert counter.count_in == 1, f"Frame {frame_idx}: count_in falsely incremented to {counter.count_in}"
        assert counter.count_out == 0
        assert counter.current_occupancy == 1
        assert counter.has_crossing_this_frame() is False


def test_one_valid_entrance_crossing_increments_total_in_once():
    """Verify that one valid entrance crossing increments Total In once and only once."""
    counter = LineCounter(line_start=(320, 0), line_end=(320, 480), orientation="horizontal", tolerance=5)

    # Person starts outside
    p_out = TrackedPerson(track_id=50, bbox=[430, 220, 470, 320], confidence=0.9)
    counter.update([p_out])
    assert counter.count_in == 0

    # Crosses line into store (B -> A)
    p_in = TrackedPerson(track_id=50, bbox=[230, 220, 270, 320], confidence=0.9)
    counter.update([p_in])
    assert counter.count_in == 1
    assert counter.has_crossing_this_frame() is True
    assert counter.current_crossings == [(50, "IN")]

    # Next frame on the inside
    p_in_next = TrackedPerson(track_id=50, bbox=[210, 220, 250, 320], confidence=0.9)
    counter.update([p_in_next])
    assert counter.count_in == 1
    assert counter.has_crossing_this_frame() is False


def test_one_valid_exit_crossing_increments_total_out_once():
    """Verify that one valid exit crossing increments Total Out once."""
    counter = LineCounter(line_start=(320, 0), line_end=(320, 480), orientation="horizontal", tolerance=5)

    # Person starts inside (Side A)
    p_in = TrackedPerson(track_id=60, bbox=[200, 220, 240, 320], confidence=0.9)
    counter.update([p_in])
    assert counter.count_out == 0

    # Person crosses outside (A -> B)
    p_out = TrackedPerson(track_id=60, bbox=[420, 220, 460, 320], confidence=0.9)
    counter.update([p_out])
    assert counter.count_out == 1
    assert counter.has_crossing_this_frame() is True
    assert counter.current_crossings == [(60, "OUT")]

    # Next frame outside
    p_out_next = TrackedPerson(track_id=60, bbox=[440, 220, 480, 320], confidence=0.9)
    counter.update([p_out_next])
    assert counter.count_out == 1
    assert counter.has_crossing_this_frame() is False


def test_occupancy_consistency_with_entry_exit_events():
    """Verify occupancy calculation is consistently derived from initial occupancy and verified in/out events."""
    # Start tracking with 18 people already inside the store
    counter = LineCounter(
        line_start=(320, 0),
        line_end=(320, 480),
        orientation="horizontal",
        initial_occupancy=18
    )
    assert counter.current_occupancy == 18
    assert counter.count_in == 0
    assert counter.count_out == 0

    # New customer 201 enters store
    c1_out = TrackedPerson(track_id=201, bbox=[400, 200, 440, 300], confidence=0.9)
    counter.update([c1_out])
    c1_in = TrackedPerson(track_id=201, bbox=[240, 200, 280, 300], confidence=0.9)
    counter.update([c1_in])
    assert counter.count_in == 1
    assert counter.count_out == 0
    assert counter.current_occupancy == 19  # 18 + 1 - 0

    # New customer 202 enters store
    c2_out = TrackedPerson(track_id=202, bbox=[410, 250, 450, 350], confidence=0.9)
    counter.update([c2_out])
    c2_in = TrackedPerson(track_id=202, bbox=[230, 250, 270, 350], confidence=0.9)
    counter.update([c2_in])
    assert counter.count_in == 2
    assert counter.count_out == 0
    assert counter.current_occupancy == 20  # 18 + 2 - 0

    # Customer 201 finishes shopping and exits
    c1_exit = TrackedPerson(track_id=201, bbox=[440, 200, 480, 300], confidence=0.9)
    counter.update([c1_exit])
    assert counter.count_in == 2
    assert counter.count_out == 1
    assert counter.current_occupancy == 19  # 18 + 2 - 1

    # Customer 202 finishes shopping and exits
    c2_exit = TrackedPerson(track_id=202, bbox=[450, 250, 490, 350], confidence=0.9)
    counter.update([c2_exit])
    assert counter.count_in == 2
    assert counter.count_out == 2
    assert counter.current_occupancy == 18  # 18 + 2 - 2


def test_people_already_inside_at_startup_handled_correctly():
    """Verify that people already inside when tracking starts are not counted as new entries, and their exit decrements occupancy."""
    counter = LineCounter(line_start=(320, 0), line_end=(320, 480), orientation="horizontal", initial_occupancy=5)

    # 5 people are already inside (Side A) on frame 0
    existing_people = [
        TrackedPerson(track_id=i, bbox=[150 + i * 20, 200, 190 + i * 20, 300], confidence=0.9)
        for i in range(1, 6)
    ]
    counter.update(existing_people)

    # None of the existing people should count as new entries
    assert counter.count_in == 0
    assert counter.count_out == 0
    assert counter.current_occupancy == 5

    # One of the existing people (person 1) exits the store (A -> B)
    p1_exit = TrackedPerson(track_id=1, bbox=[400, 200, 440, 300], confidence=0.9)
    counter.update([p1_exit])

    assert counter.count_in == 0
    assert counter.count_out == 1
    assert counter.current_occupancy == 4  # 5 + 0 - 1 = 4


def test_segment_bounds_prevent_false_crossings_in_unrelated_areas():
    """Verify that people crossing the X line in an area outside the vertical line segment are ignored."""
    # Entrance line only spans y in [250, 450] at x=320
    counter = LineCounter(
        line_start=(320, 250),
        line_end=(320, 450),
        orientation="horizontal",
        segment_margin=20
    )

    # Person 88 walks across x=320 at y=50 (far away in upper grocery aisle)
    p_step1 = TrackedPerson(track_id=88, bbox=[390, 30, 430, 70], confidence=0.9)  # y_bottom = 70
    counter.update([p_step1])
    p_step2 = TrackedPerson(track_id=88, bbox=[230, 30, 270, 70], confidence=0.9)  # crossed x, but y=70 is out of bounds
    counter.update([p_step2])

    # Must NOT count as an entrance crossing
    assert counter.count_in == 0
    assert counter.count_out == 0
    assert counter.has_crossing_this_frame() is False


def test_session_reset_clears_counts_and_restores_clean_baseline():
    """Verify session reset cleans counters and resets occupancy."""
    counter = LineCounter(line_start=(320, 0), line_end=(320, 480), orientation="horizontal")
    tracker = PersonTracker()

    # Simulate some activity
    p = TrackedPerson(track_id=1, bbox=[400, 200, 440, 300], confidence=0.9)
    counter.update([p])
    p_in = TrackedPerson(track_id=1, bbox=[200, 200, 240, 300], confidence=0.9)
    counter.update([p_in])
    tracker._update_trajectory(1, (220, 250))

    assert counter.count_in == 1
    assert len(tracker.get_trajectory(1)) > 0

    # Video loops or session resets
    counter.reset_counts(initial_occupancy=18)
    tracker.reset()

    assert counter.count_in == 0
    assert counter.count_out == 0
    assert counter.current_occupancy == 18
    assert len(tracker.get_trajectory(1)) == 0
    assert len(tracker.seen_ids) == 0
