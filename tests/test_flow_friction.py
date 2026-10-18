# tests/test_flow_friction.py
# StorePulse AI — Automated Unit Tests for Flow Friction Score Engine
# Developer: Omkar Gurav

import pytest
from backend.flow_friction import FlowFrictionCalculator, friction_calculator


def test_friction_score_bounds_and_structure():
    zone_stats = {
        "zone_1": {
            "zone_name": "Entrance Area",
            "current_occupancy": 8,
            "capacity": 10,
            "avg_dwell_seconds": 45.0,
            "dwell_alert_seconds": 60.0,
        }
    }
    scores = friction_calculator.calculate(zone_stats, queue_count=2, queue_threshold=3)
    assert "zone_1" in scores
    score_data = scores["zone_1"]

    assert 0 <= score_data["friction_score"] <= 100
    assert "severity" in score_data
    assert score_data["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert "breakdown" in score_data
    assert "occupancy_ratio" in score_data["breakdown"]
    assert "dwell_ratio" in score_data["breakdown"]
    assert "recommendation" in score_data


def test_friction_high_occupancy_triggers_high_score():
    # Exceed capacity significantly
    zone_stats = {
        "zone_crowded": {
            "zone_name": "Bottleneck Hallway",
            "zone_type": "checkout",
            "current_occupancy": 20,
            "capacity": 5,
            "avg_dwell_seconds": 180.0,
            "sample_count": 15,
            "dwell_alert_seconds": 30.0,
        }
    }
    scores = friction_calculator.calculate(zone_stats, queue_count=8, queue_threshold=3)
    score_data = scores["zone_crowded"]

    assert score_data["friction_score"] >= 70
    assert score_data["severity"] in ("HIGH", "CRITICAL")


def test_friction_missing_or_empty_data():
    empty_stats = {}
    scores = friction_calculator.calculate(empty_stats, queue_count=0, queue_threshold=3)
    assert isinstance(scores, dict)
    assert len(scores) == 0

    store_score = friction_calculator.get_store_level_score(scores)
    assert store_score["store_friction_score"] == 0.0
    assert store_score["status"] == "NORMAL"


def test_friction_store_level_aggregation():
    scores = {
        "z1": {"friction_score": 20.0, "severity": "LOW"},
        "z2": {"friction_score": 60.0, "severity": "HIGH"},
    }
    store_summary = friction_calculator.get_store_level_score(scores)
    assert store_summary["store_friction_score"] == 40.0
    assert store_summary["max_zone_score"] == 60.0
    assert store_summary["high_friction_zones"] == ["z2"]
