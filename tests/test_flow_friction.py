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


def test_friction_bounds_determinism_and_explainability():
    """Requirement 8: Flow Friction Score bounds [0, 100], determinism, and explainability."""
    calc = FlowFrictionCalculator()

    # Extreme extreme overcrowding
    extreme_stats = {
        "mega_bottleneck": {
            "zone_name": "Main Entrance",
            "zone_type": "entrance",
            "current_occupancy": 500,
            "capacity": 5,
            "avg_dwell_seconds": 9999.0,
            "sample_count": 20,
            "dwell_alert_seconds": 10.0,
            "bottleneck": {
                "is_bottleneck": True,
                "severity": "CRITICAL",
                "evidence": ["Occupancy at 10000% of capacity", "Sustained congestion 60s"],
                "recommendation": "Deploy staff immediately to ease queue"
            }
        }
    }
    scores_1 = calc.calculate(extreme_stats, queue_count=50, queue_threshold=5)
    score_data = scores_1["mega_bottleneck"]

    # 1. Bounded strictly between 0 and 100
    assert 0.0 <= score_data["friction_score"] <= 100.0
    assert score_data["friction_score"] >= 70.0
    assert score_data["severity"] in ("HIGH", "CRITICAL")

    # 2. Determinism: identical inputs must yield identical scores
    scores_2 = calc.calculate(extreme_stats, queue_count=50, queue_threshold=5)
    assert scores_1["mega_bottleneck"]["friction_score"] == scores_2["mega_bottleneck"]["friction_score"]

    # 3. Factor breakdown and explainability
    breakdown = score_data["breakdown"]
    assert "occupancy_ratio" in breakdown
    assert "dwell_ratio" in breakdown
    assert "queue_ratio" in breakdown
    assert "explanation" in score_data
    assert "Deploy staff immediately" in score_data["recommendation"]

    # 4. Zero / Empty condition
    zero_stats = {
        "empty_zone": {
            "zone_name": "Quiet Corner",
            "zone_type": "browsing",
            "current_occupancy": 0,
            "capacity": 10,
            "avg_dwell_seconds": 0.0,
            "sample_count": 0,
            "dwell_alert_seconds": 60.0,
        }
    }
    zero_score = calc.calculate(zero_stats, queue_count=0, queue_threshold=5)["empty_zone"]
    assert zero_score["friction_score"] == 0.0
    assert zero_score["severity"] == "LOW"
    assert zero_score["data_confidence"] == "LOW"

