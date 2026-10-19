# queue_monitor.py
# ============================================================
# Monitor the number of people in a specific zone (cashier, entrance, etc).
#
# How it works:
# 1. Define a zone as a rectangle (frame ratio)
# 2. Every frame, count how many Track IDs have their bottom_center
#    inside the zone
# 3. If it exceeds the threshold -> alert
#
# Why use ratios and not pixels?
# So the zone is portable across different video resolutions.
# Whether the video is 640x480 or 1920x1080, the zone remains in the same
# proportional position.
# ============================================================

import cv2
import numpy as np
from typing import List, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import deque
import time

try:
    from analytics import config
except ImportError:
    import config


@dataclass
class QueueState:
    """Snapshot of the queue state at a single point in time."""
    count: int
    timestamp: float
    is_alert: bool


class QueueMonitor:

    def __init__(
        self,
        frame_width: int,
        frame_height: int,
        zone_ratio: Optional[Tuple[float, float, float, float]] = None,
        alert_threshold: Optional[int] = None,
    ):
        self.frame_width = max(1, frame_width)
        self.frame_height = max(1, frame_height)

        self.zone_ratio = (
            zone_ratio
            if zone_ratio is not None
            else getattr(config, 'QUEUE_ZONE', (0.13, 0.15, 0.37, 0.50))
        )
        self.zone_px = self._ratio_to_pixel(self.zone_ratio)

        self.alert_threshold = (
            alert_threshold
            if alert_threshold is not None
            else getattr(config, 'QUEUE_ALERT_THRESHOLD', 3)
        )

        # Current state
        self.current_count = 0
        self.is_alert = False

        # Count history for charts (rolling window)
        self.history: deque = deque(maxlen=60)

        # Track IDs currently in the zone
        self.ids_in_zone: Set[int] = set()

        print(f"[Queue] Zone px: {self.zone_px}, alert threshold: {self.alert_threshold}")

    def _ratio_to_pixel(self, zone_ratio: Tuple) -> Tuple[int, int, int, int]:
        """Convert a zone (ratio 0-1) to pixel coordinates."""
        rx1, ry1, rx2, ry2 = zone_ratio
        return (
            int(rx1 * self.frame_width),
            int(ry1 * self.frame_height),
            int(rx2 * self.frame_width),
            int(ry2 * self.frame_height),
        )

    def update(self, tracked_persons) -> int:
        """
        Count the people inside the zone.

        Args:
            tracked_persons: list of TrackedPerson from the tracker

        Returns:
            the current number of people in the zone
        """
        x1, y1, x2, y2 = self.zone_px
        self.ids_in_zone = set()

        if not tracked_persons:
            self.current_count = 0
            self.is_alert = False
            return 0

        for person in tracked_persons:
            if person is None:
                continue

            # Support both bottom_center property or tuple/bbox
            bc = getattr(person, 'bottom_center', None)
            if bc is None and hasattr(person, 'center'):
                bc = person.center
            elif bc is None and hasattr(person, 'bbox') and len(person.bbox) >= 4:
                bc = (int((person.bbox[0] + person.bbox[2]) / 2), int(person.bbox[3]))

            if bc is None:
                continue

            bcx, bcy = bc
            # Check if bottom_center is inside the zone
            if x1 <= bcx <= x2 and y1 <= bcy <= y2:
                tid = getattr(person, 'track_id', id(person))
                self.ids_in_zone.add(tid)

        self.current_count = len(self.ids_in_zone)
        self.is_alert = self.current_count >= self.alert_threshold


        # Save to history
        self.history.append(QueueState(
            count=self.current_count,
            timestamp=time.time(),
            is_alert=self.is_alert
        ))

        return self.current_count

    def is_in_zone(self, track_id: int) -> bool:
        return track_id in self.ids_in_zone

    def draw_zone(self, frame: np.ndarray) -> np.ndarray:
        """
        Draw the zone overlay on the frame.
        Color changes when there's an alert.
        """
        x1, y1, x2, y2 = self.zone_px
        color = config.QUEUE_ZONE_COLOR_ALERT if self.is_alert else config.QUEUE_ZONE_COLOR

        # Semi-transparent fill
        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
        cv2.addWeighted(overlay, config.QUEUE_ZONE_ALPHA, frame, 1 - config.QUEUE_ZONE_ALPHA, 0, frame)

        # Border
        thickness = 3 if self.is_alert else 1
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

        # Label
        label = f"QUEUE: {self.current_count}"
        if self.is_alert:
            label += " (!)"

        cv2.putText(
            frame, label,
            (x1 + 5, y1 - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55,
            color, 2, cv2.LINE_AA
        )

        return frame

    def get_avg_count(self, last_n: int = 30) -> float:
        """Average number of people in the zone over the last N snapshots."""
        if not self.history:
            return 0.0
        recent = list(self.history)[-last_n:]
        return sum(s.count for s in recent) / len(recent)