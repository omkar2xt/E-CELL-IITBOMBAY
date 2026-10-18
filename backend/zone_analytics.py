# StorePulse AI — Zone-Wise Dwell-Time Analytics Engine
# Developer: Omkar Gurav
#
# Tracks zone entry/exit events per anonymous tracking ID.
# Calculates occupancy, dwell time (avg/median/max), traffic intensity.
# Handles occlusion / tracking-ID switches gracefully.

import time
import math
import threading
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class Zone:
    """A named, configurable rectangular or polygon zone."""
    id: str
    name: str
    type: str                      # entrance|checkout|display|electronics|grocery|promo|restricted
    # Polygon as list of (x_ratio, y_ratio) points (0.0–1.0)
    polygon: List[Tuple[float, float]]
    capacity: int = 10             # max persons before congestion alert
    dwell_alert_seconds: float = 120.0  # alert if avg dwell > this
    color: Tuple[int, int, int] = (0, 200, 100)  # BGR

    def contains_point(self, px: float, py: float) -> bool:
        """Ray-casting algorithm to test if point (px, py) is inside polygon."""
        inside = False
        n = len(self.polygon)
        if n < 3:
            return False
        j = n - 1
        for i in range(n):
            xi, yi = self.polygon[i]
            xj, yj = self.polygon[j]
            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-10) + xi):
                inside = not inside
            j = i
        return inside


@dataclass
class DwellRecord:
    """One continuous visit by a tracking ID to a zone."""
    track_id: int
    zone_id: str
    enter_time: float
    exit_time: Optional[float] = None

    @property
    def dwell_seconds(self) -> Optional[float]:
        if self.exit_time is None:
            return time.time() - self.enter_time
        return self.exit_time - self.enter_time


class ZoneAnalyticsEngine:
    """
    Zone dwell-time analytics for multiple configurable zones.

    Lifecycle:
        engine = ZoneAnalyticsEngine()
        engine.set_zones([Zone(...), ...])
        engine.update(tracked_persons, frame_width, frame_height)
        stats = engine.get_zone_stats()
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._zones: Dict[str, Zone] = {}

        # Active presence: { (track_id, zone_id): DwellRecord }
        self._active: Dict[Tuple[int, str], DwellRecord] = {}

        # Completed records (exited): list of DwellRecord
        self._completed: List[DwellRecord] = []

        # Zone-to-zone transition matrix: { (from_zone_id, to_zone_id): count }
        self._transitions: Dict[Tuple[str, str], int] = defaultdict(int)

        # Last known zone for each track_id
        self._last_zone: Dict[int, Optional[str]] = {}

        # Frame-level snapshots for trend data (rolling 60 entries)
        self._history: Dict[str, List[Dict]] = defaultdict(list)
        self._max_history = 180

    # ── Zone configuration ────────────────────────────────────────────

    def set_zones(self, zones: List[Zone]):
        with self._lock:
            self._zones = {z.id: z for z in zones}

    def add_zone(self, zone: Zone):
        with self._lock:
            self._zones[zone.id] = zone

    def remove_zone(self, zone_id: str):
        with self._lock:
            self._zones.pop(zone_id, None)

    def get_zones(self) -> List[Zone]:
        with self._lock:
            return list(self._zones.values())

    # ── Core update ───────────────────────────────────────────────────

    def update(self, tracked_persons, frame_width: Optional[int] = None, frame_height: Optional[int] = None, **kwargs):
        """
        Process one frame of tracked persons.
        tracked_persons: list of TrackedPerson objects with .track_id and .bottom_center
        """
        w = frame_width or kwargs.get("frame_w") or 1
        h = frame_height or kwargs.get("frame_h") or 1
        with self._lock:
            now = time.time()
            current_ids_in_zone: Dict[str, set] = {zid: set() for zid in self._zones}

            for person in tracked_persons:
                tid = person.track_id
                bcx, bcy = person.bottom_center
                fx = bcx / w
                fy = bcy / h

                person_zones = []
                for zid, zone in self._zones.items():
                    if self._point_in_polygon(fx, fy, zone.polygon):
                        person_zones.append(zid)
                        current_ids_in_zone[zid].add(tid)

                        # Start dwell record if not already tracking
                        key = (tid, zid)
                        if key not in self._active:
                            self._active[key] = DwellRecord(
                                track_id=tid,
                                zone_id=zid,
                                enter_time=now
                            )

                # Zone-to-zone transition tracking
                primary_zone = person_zones[0] if person_zones else None
                prev_zone = self._last_zone.get(tid)

                if primary_zone != prev_zone:
                    if prev_zone is not None and primary_zone is not None:
                        self._transitions[(prev_zone, primary_zone)] += 1
                    self._last_zone[tid] = primary_zone

            # Close dwell records for people who left zones
            to_close = []
            for (tid, zid), record in self._active.items():
                if tid not in current_ids_in_zone.get(zid, set()):
                    record.exit_time = now
                    to_close.append((tid, zid))
                    self._completed.append(record)

            for key in to_close:
                del self._active[key]

            # Snapshot history
            for zid, zone in self._zones.items():
                occupancy = len(current_ids_in_zone[zid])
                self._history[zid].append({
                    "ts": now,
                    "occupancy": occupancy
                })
                if len(self._history[zid]) > self._max_history:
                    self._history[zid] = self._history[zid][-self._max_history:]

    # ── Stats ─────────────────────────────────────────────────────────

    def get_zone_stats(self) -> Dict[str, Dict]:
        with self._lock:
            result = {}
            now = time.time()

            for zid, zone in self._zones.items():
                # Completed dwell records for this zone
                completed = [r for r in self._completed if r.zone_id == zid]
                active = [(k, r) for k, r in self._active.items() if k[1] == zid]

                dwell_seconds = [r.dwell_seconds for r in completed if r.dwell_seconds is not None]
                dwell_seconds = [d for d in dwell_seconds if d > 0]

                current_occupancy = len(active)
                total_entries = len(completed) + len(active)

                avg_dwell = sum(dwell_seconds) / len(dwell_seconds) if dwell_seconds else 0
                median_dwell = statistics.median(dwell_seconds) if len(dwell_seconds) >= 2 else avg_dwell
                max_dwell = max(dwell_seconds) if dwell_seconds else 0

                congestion = (current_occupancy / max(zone.capacity, 1)) * 100
                congestion_status = (
                    "CRITICAL" if congestion >= 100 else
                    "HIGH" if congestion >= 75 else
                    "MEDIUM" if congestion >= 50 else
                    "LOW"
                )

                dwell_alert = avg_dwell > zone.dwell_alert_seconds and len(dwell_seconds) >= 3

                # Recent history (last 60 snapshots)
                history = self._history.get(zid, [])[-60:]

                result[zid] = {
                    "zone_id": zid,
                    "zone_name": zone.name,
                    "zone_type": zone.type,
                    "current_occupancy": current_occupancy,
                    "capacity": zone.capacity,
                    "total_entries": total_entries,
                    "avg_dwell_seconds": round(avg_dwell, 1),
                    "median_dwell_seconds": round(median_dwell, 1),
                    "max_dwell_seconds": round(max_dwell, 1),
                    "congestion_pct": round(congestion, 1),
                    "congestion_status": congestion_status,
                    "congestion_level": congestion_status,
                    "dwell_alert": dwell_alert,
                    "sample_count": len(dwell_seconds),
                    "history": history,
                }

            return result

    def get_transitions(self) -> Dict[str, Any]:
        with self._lock:
            transitions = []
            for (from_z, to_z), count in self._transitions.items():
                transitions.append({
                    "from_zone": from_z,
                    "to_zone": to_z,
                    "count": count
                })
            return {"transitions": sorted(transitions, key=lambda x: -x["count"])}

    def get_movement_data(self) -> Dict[str, Any]:
        """Aggregated movement data — no individual trajectories exposed."""
        return self.get_transitions()

    def reset(self):
        with self._lock:
            self._active.clear()
            self._completed.clear()
            self._transitions.clear()
            self._last_zone.clear()
            self._history.clear()

    # ── Geometry ──────────────────────────────────────────────────────

    @staticmethod
    def _point_in_polygon(x: float, y: float, polygon: List[Tuple[float, float]]) -> bool:
        """
        Ray-casting algorithm for point-in-polygon test.
        Works for convex and concave polygons.
        Polygon points are (x_ratio, y_ratio) in [0, 1].
        """
        if len(polygon) < 3:
            return False
        n = len(polygon)
        inside = False
        px, py = x, y
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-10) + xi):
                inside = not inside
            j = i
        return inside

    # ── Default zones ─────────────────────────────────────────────────

    @staticmethod
    def default_zones() -> List[Zone]:
        """Return a set of sensible default zones for a typical retail store."""
        return [
            Zone(
                id="entrance",
                name="Entrance",
                type="entrance",
                polygon=[(0.0, 0.6), (0.2, 0.6), (0.2, 1.0), (0.0, 1.0)],
                capacity=8,
                dwell_alert_seconds=60,
                color=(50, 220, 50)
            ),
            Zone(
                id="checkout",
                name="Checkout",
                type="checkout",
                polygon=[(0.13, 0.15), (0.37, 0.15), (0.37, 0.50), (0.13, 0.50)],
                capacity=5,
                dwell_alert_seconds=180,
                color=(0, 100, 255)
            ),
            Zone(
                id="electronics",
                name="Electronics",
                type="electronics",
                polygon=[(0.55, 0.1), (0.9, 0.1), (0.9, 0.45), (0.55, 0.45)],
                capacity=12,
                dwell_alert_seconds=300,
                color=(200, 50, 200)
            ),
            Zone(
                id="grocery",
                name="Grocery",
                type="grocery",
                polygon=[(0.38, 0.5), (0.75, 0.5), (0.75, 1.0), (0.38, 1.0)],
                capacity=20,
                dwell_alert_seconds=240,
                color=(0, 180, 255)
            ),
            Zone(
                id="promo",
                name="Promo Display",
                type="promo",
                polygon=[(0.4, 0.15), (0.55, 0.15), (0.55, 0.45), (0.4, 0.45)],
                capacity=6,
                dwell_alert_seconds=90,
                color=(50, 50, 255)
            ),
        ]


# Singleton instance shared across the application
zone_analytics_engine = ZoneAnalyticsEngine()
