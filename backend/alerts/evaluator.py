# StorePulse AI — Alert Condition Evaluator
# Developer: Omkar Gurav
# Evaluates live CV pipeline state and triggers deduplicated alerts with evidence frames

import time
from typing import Dict, Any, Optional
import numpy as np

from backend.alerts.service import alert_service

class AlertEvaluator:
    """
    Evaluates real-time CV analytics telemetry against store operational rules.
    Invoked periodically by the pipeline without degrading video frame rate.
    """

    def evaluate_pipeline_state(
        self,
        payload: Dict[str, Any],
        frame: Optional[np.ndarray] = None,
        source_mode: str = "demo"
    ):
        """
        Evaluate current metrics and dispatch alerts if thresholds are breached.
        """
        if not payload:
            return

        now = time.time()
        queue_count = payload.get("queue_count", 0)
        queue_alert = payload.get("queue_alert", False)
        zone_stats = payload.get("zone_stats", {})
        bottlenecks = payload.get("bottlenecks", {})

        # ── 1. Queue Threshold Evaluation ─────────────────────────────
        alert_threshold = 3  # Standard threshold
        if queue_alert or queue_count >= alert_threshold:
            sev = "CRITICAL" if queue_count >= (alert_threshold + 2) else "HIGH"
            alert_service.trigger_alert(
                alert_type="queue_threshold_exceeded",
                severity=sev,
                metric_name="queue_count",
                metric_value=queue_count,
                threshold_value=alert_threshold,
                message=f"Checkout queue exceeded threshold: {queue_count} waiting (threshold: {alert_threshold})",
                zone_id="checkout",
                source_mode=source_mode,
                frame=frame,
                cooldown_seconds=25.0,
                metadata={
                    "queue_count": queue_count,
                    "threshold": alert_threshold,
                    "recommendation": "Deploy an additional cashier or open self-checkout lane."
                }
            )
        else:
            alert_service.resolve_alert("queue_threshold_exceeded", zone_id="checkout")

        # ── 2. Zone Capacity & Dwell Evaluations ──────────────────────
        for zid, z in zone_stats.items():
            zname = z.get("zone_name", zid)
            occ = z.get("current_occupancy", 0)
            capacity = z.get("capacity", 10)
            dwell_alert_sec = z.get("dwell_alert_seconds", 120.0)
            max_dwell = z.get("max_active_dwell", 0.0)

            # Capacity Check
            if capacity > 0 and occ >= capacity:
                sev = "CRITICAL" if occ >= int(capacity * 1.5) else "HIGH"
                alert_service.trigger_alert(
                    alert_type="zone_capacity_exceeded",
                    severity=sev,
                    metric_name="current_occupancy",
                    metric_value=occ,
                    threshold_value=capacity,
                    message=f"Zone capacity exceeded at {zname}: {occ}/{capacity} occupants",
                    zone_id=zid,
                    source_mode=source_mode,
                    frame=frame,
                    cooldown_seconds=30.0,
                    metadata={"zone_id": zid, "occupancy": occ, "capacity": capacity}
                )
            else:
                alert_service.resolve_alert("zone_capacity_exceeded", zone_id=zid)

            # Excessive Dwell Check
            if dwell_alert_sec > 0 and max_dwell >= dwell_alert_sec:
                alert_service.trigger_alert(
                    alert_type="excessive_dwell_time",
                    severity="MEDIUM",
                    metric_name="max_active_dwell",
                    metric_value=round(max_dwell, 1),
                    threshold_value=dwell_alert_sec,
                    message=f"Excessive customer dwell at {zname}: lingering for {max_dwell:.1f}s (threshold: {dwell_alert_sec}s)",
                    zone_id=zid,
                    source_mode=source_mode,
                    frame=frame,
                    cooldown_seconds=45.0,
                    metadata={"zone_id": zid, "max_dwell_seconds": max_dwell, "threshold": dwell_alert_sec}
                )
            else:
                alert_service.resolve_alert("excessive_dwell_time", zone_id=zid)

        # ── 3. Bottleneck State Machine Evaluations ───────────────────
        for zid, b in bottlenecks.items():
            if b.get("is_bottleneck"):
                sev = b.get("severity", "HIGH").upper()
                dur = b.get("congested_duration", 0.0)
                rec = b.get("recommendation", "Assist customer flow immediately.")
                zname = b.get("zone_name", zid)

                alert_service.trigger_alert(
                    alert_type="bottleneck_detected",
                    severity=sev,
                    metric_name="congested_duration",
                    metric_value=round(dur, 1),
                    threshold_value=5.0,
                    message=f"Bottleneck detected at {zname}: {rec}",
                    zone_id=zid,
                    source_mode=source_mode,
                    frame=frame,
                    cooldown_seconds=30.0,
                    metadata={
                        "zone_id": zid,
                        "duration_seconds": dur,
                        "evidence": b.get("evidence", []),
                        "recommendation": rec
                    }
                )
            else:
                alert_service.resolve_alert("bottleneck_detected", zone_id=zid)

# Global evaluator instance
alert_evaluator = AlertEvaluator()
