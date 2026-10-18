# StorePulse AI — Flow Friction Score Engine
# Developer: Omkar Gurav
#
# IMPORTANT: This is a prototype decision-support metric, not a validated
# industry standard. All thresholds are configurable defaults. Weights
# should be calibrated using observed footage and manually reviewed examples.
#
# Score scale: 0 (no friction) — 100 (maximum congestion/friction)

import time
import threading
from collections import deque, defaultdict
from typing import Dict, List, Optional, Any


class FrictionConfig:
    """
    Configurable weights and thresholds for the Flow Friction Score.
    Each component is documented with its meaning.
    """

    # Component weights (should sum to ~1.0 but are normalized internally)
    WEIGHT_OCCUPANCY = 0.35     # Occupancy relative to zone capacity
    WEIGHT_DWELL = 0.30         # Avg dwell time relative to zone baseline
    WEIGHT_QUEUE = 0.20         # Queue buildup (checkout-specific)
    WEIGHT_CONGESTION = 0.15    # Rapid occupancy changes

    # Dwell-time baselines per zone type (seconds)
    # These are configurable starting points, not validated standards
    DWELL_BASELINES = {
        "entrance":    30,
        "checkout":   120,
        "electronics": 180,
        "grocery":    120,
        "promo":       60,
        "display":     90,
        "restricted":  10,
        "default":     90,
    }

    # Occupancy above this fraction of capacity = full congestion contribution
    OCCUPANCY_SATURATE_AT = 1.2   # 120% of capacity → maximum occupancy score

    # Dwell above this multiple of baseline = maximum dwell contribution
    DWELL_SATURATE_AT = 3.0       # 3× baseline → maximum dwell score

    # History length for score trend (entries)
    HISTORY_LENGTH = 120

    # Alert thresholds
    ALERT_THRESHOLD_CRITICAL = 75
    ALERT_THRESHOLD_HIGH = 50
    ALERT_THRESHOLD_MEDIUM = 25


class FlowFrictionCalculator:
    """
    Calculates per-zone Flow Friction Scores from zone analytics data.

    Inputs:
        zone_stats: Dict returned by ZoneAnalyticsEngine.get_zone_stats()
        queue_count: current checkout queue count (int)
        queue_threshold: queue alert threshold (int)

    Output (per zone):
        {
          "score": float,          # 0–100
          "components": { ... },   # contributing factors with individual scores
          "alert_level": str,      # NONE / MEDIUM / HIGH / CRITICAL
          "explanation": str,      # human-readable explanation
          "recommendation": str,   # suggested action
          "data_confidence": str,  # LOW / MEDIUM / HIGH
        }
    """

    def __init__(self, config: Optional[FrictionConfig] = None):
        self.config = config or FrictionConfig()
        self._lock = threading.Lock()
        self._history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.config.HISTORY_LENGTH))

    def calculate(
        self,
        zone_stats: Dict[str, Dict],
        queue_count: int = 0,
        queue_threshold: int = 3,
    ) -> Dict[str, Dict]:
        """
        Calculate friction scores for all zones.
        Returns a dict keyed by zone_id.
        """
        cfg = self.config
        results = {}
        now = time.time()

        for zone_id, stats in zone_stats.items():
            zone_type = stats.get("zone_type", "default")
            occupancy = stats.get("current_occupancy", 0)
            capacity = max(stats.get("capacity", 10), 1)
            avg_dwell = stats.get("avg_dwell_seconds", 0)
            sample_count = stats.get("sample_count", 0)
            baseline = cfg.DWELL_BASELINES.get(zone_type, cfg.DWELL_BASELINES["default"])

            # ── Component 1: Occupancy ────────────────────────────────
            occ_ratio = occupancy / capacity
            occ_score = min(100, (occ_ratio / cfg.OCCUPANCY_SATURATE_AT) * 100)

            # ── Component 2: Dwell time ───────────────────────────────
            if sample_count >= 3 and avg_dwell > 0:
                dwell_ratio = avg_dwell / baseline
                dwell_score = min(100, ((dwell_ratio - 1.0) / (cfg.DWELL_SATURATE_AT - 1.0)) * 100)
                dwell_score = max(0, dwell_score)
                dwell_confidence = "HIGH" if sample_count >= 10 else "MEDIUM"
            else:
                dwell_score = 0
                dwell_confidence = "LOW"

            # ── Component 3: Queue (only for checkout zones) ──────────
            if zone_type == "checkout":
                queue_ratio = queue_count / max(queue_threshold, 1)
                queue_score = min(100, queue_ratio * 100)
            else:
                queue_score = 0

            # ── Weighted average ───────────────────────────────────────
            total_weight = cfg.WEIGHT_OCCUPANCY + cfg.WEIGHT_DWELL + cfg.WEIGHT_QUEUE
            score = (
                occ_score * cfg.WEIGHT_OCCUPANCY +
                dwell_score * cfg.WEIGHT_DWELL +
                queue_score * cfg.WEIGHT_QUEUE
            ) / total_weight

            score = round(min(100, max(0, score)), 1)

            # ── Alert level ────────────────────────────────────────────
            if score >= cfg.ALERT_THRESHOLD_CRITICAL:
                alert_level = "CRITICAL"
            elif score >= cfg.ALERT_THRESHOLD_HIGH:
                alert_level = "HIGH"
            elif score >= cfg.ALERT_THRESHOLD_MEDIUM:
                alert_level = "MEDIUM"
            else:
                alert_level = "NONE"

            # ── Explanation ────────────────────────────────────────────
            factors = []
            if occ_score >= 60:
                factors.append(f"high occupancy ({occupancy}/{capacity})")
            if dwell_score >= 60 and dwell_confidence != "LOW":
                factors.append(f"prolonged dwell ({avg_dwell:.0f}s vs {baseline}s baseline)")
            if queue_score >= 60:
                factors.append(f"queue buildup ({queue_count} in queue)")
            explanation = (
                "Main factors: " + ", ".join(factors)
                if factors else "Flow is smooth"
            )

            # ── Recommendation ─────────────────────────────────────────
            recommendation = _get_recommendation(alert_level, zone_type, factors)

            # ── Data confidence ────────────────────────────────────────
            if sample_count >= 10:
                data_confidence = "HIGH"
            elif sample_count >= 3:
                data_confidence = "MEDIUM"
            else:
                data_confidence = "LOW"

            # ── Store history ──────────────────────────────────────────
            with self._lock:
                self._history[zone_id].append({"ts": now, "score": score})

            results[zone_id] = {
                "zone_id": zone_id,
                "zone_name": stats.get("zone_name", zone_id),
                "score": score,
                "friction_score": score,
                "severity": alert_level if alert_level != "NONE" else "LOW",
                "breakdown": {
                    "occupancy_ratio": round(occ_score, 1),
                    "dwell_ratio": round(dwell_score, 1),
                    "queue_ratio": round(queue_score, 1),
                },
                "components": {
                    "occupancy_score": round(occ_score, 1),
                    "dwell_score": round(dwell_score, 1),
                    "queue_score": round(queue_score, 1),
                    "weights": {
                        "occupancy": cfg.WEIGHT_OCCUPANCY,
                        "dwell": cfg.WEIGHT_DWELL,
                        "queue": cfg.WEIGHT_QUEUE,
                    }
                },
                "alert_level": alert_level,
                "explanation": explanation,
                "recommendation": recommendation,
                "data_confidence": data_confidence,
                "disclaimer": (
                    "Prototype heuristic metric. Weights and thresholds are "
                    "configurable defaults, not validated industry benchmarks."
                ),
                "history": list(self._history[zone_id]),
            }

        return results

    def get_store_level_score(self, zone_scores: Dict[str, Dict]) -> Dict:
        """Aggregate all zone scores into a single store-level metric."""
        if not zone_scores:
            return {
                "score": 0.0,
                "store_friction_score": 0.0,
                "peak_score": 0.0,
                "max_zone_score": 0.0,
                "alert_level": "NONE",
                "status": "NORMAL",
                "zone_count": 0,
                "high_friction_zones": [],
            }

        scores = [
            v.get("score") if "score" in v else v.get("friction_score", 0.0)
            for v in zone_scores.values()
        ]
        avg = round(sum(scores) / len(scores), 1)
        peak = round(max(scores), 1)

        high_zones = [
            zid for zid, v in zone_scores.items()
            if (v.get("score") or v.get("friction_score", 0)) >= FrictionConfig.ALERT_THRESHOLD_HIGH
            or v.get("severity") in ("HIGH", "CRITICAL")
            or v.get("alert_level") in ("HIGH", "CRITICAL")
        ]

        if peak >= FrictionConfig.ALERT_THRESHOLD_CRITICAL:
            alert = "CRITICAL"
        elif peak >= FrictionConfig.ALERT_THRESHOLD_HIGH:
            alert = "HIGH"
        elif peak >= FrictionConfig.ALERT_THRESHOLD_MEDIUM:
            alert = "MEDIUM"
        else:
            alert = "NONE"

        return {
            "score": avg,
            "store_friction_score": avg,
            "peak_score": peak,
            "max_zone_score": peak,
            "alert_level": alert,
            "status": "CONGESTED" if alert in ("HIGH", "CRITICAL") else ("CAUTION" if alert == "MEDIUM" else "NORMAL"),
            "zone_count": len(scores),
            "high_friction_zones": high_zones,
        }


def _get_recommendation(alert_level: str, zone_type: str, factors: List[str]) -> str:
    """Generate a human-readable operational recommendation."""
    if alert_level == "NONE":
        return "No action needed. Zone is operating normally."

    recs = {
        "checkout": {
            "CRITICAL": "Immediately open additional checkout registers and redirect staff.",
            "HIGH": "Consider opening another register or deploying a staff member to assist.",
            "MEDIUM": "Monitor checkout area closely. Prepare to open another lane.",
        },
        "entrance": {
            "CRITICAL": "Entrance is heavily congested. Deploy staff to manage crowd flow.",
            "HIGH": "Entrance becoming congested. Monitor and prepare crowd management.",
            "MEDIUM": "Slight congestion at entrance. Keep pathways clear.",
        },
        "default": {
            "CRITICAL": "Zone critically congested. Immediate staff intervention recommended.",
            "HIGH": "Zone highly congested. Consider redistributing customers or stock.",
            "MEDIUM": "Zone moderately congested. Monitor and take preventive action.",
        }
    }

    zone_recs = recs.get(zone_type, recs["default"])
    return zone_recs.get(alert_level, "Review zone for potential improvements.")


# Singleton instance
friction_calculator = FlowFrictionCalculator()
