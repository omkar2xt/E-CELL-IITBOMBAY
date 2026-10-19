# StorePulse AI — Zone-Wise Dwell-Time & Bottleneck Analytics Engine
# Developer: Omkar Gurav
#
# Tracks zone entry/exit events per anonymous tracking ID.
# Implements boundary hysteresis, track interruption recovery, and
# elapsed timestamp dwell calculation (active vs. completed).
# Detects bottlenecks using multi-factor explainable evidence with persistence.

import time
import math
import threading
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set


@dataclass
class Zone:
    """A named, configurable retail store polygon zone."""
    id: str
    name: str
    type: str                                # entrance|checkout|display|electronics|grocery|promo|aisle|restricted
    polygon: List[Tuple[float, float]]       # Polygon as list of (x_ratio, y_ratio) points (0.0–1.0)
    capacity: int = 10                       # Max persons before congestion alert
    dwell_alert_seconds: float = 120.0       # Threshold for excessive dwell time
    congestion_threshold_ratio: float = 0.85 # Occupancy/capacity ratio triggering congestion warning
    color: Tuple[int, int, int] = (0, 200, 100) # BGR display color

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
    """One continuous visit by an anonymous tracking ID to a zone."""
    track_id: int
    zone_id: str
    enter_time: float
    last_seen_time: float = 0.0
    exit_time: Optional[float] = None
    interrupted: bool = False
    long_dwell_flagged: bool = False

    def dwell_seconds(self, current_time: Optional[float] = None, now: Optional[float] = None) -> float:
        """Calculate elapsed dwell time safely without negative or absurd jumps."""
        t = current_time if current_time is not None else (now if now is not None else time.time())
        end = self.exit_time if self.exit_time is not None else t
        elapsed = end - self.enter_time
        # Guard against negative time (e.g. video rewind) or extreme stale values (> 24 hours)
        if elapsed < 0:
            return 0.0
        return min(elapsed, 86400.0)


@dataclass
class BottleneckState:
    """Tracks sustained congestion and persistence to prevent alert flickering."""
    is_bottleneck: bool = False
    severity: str = "LOW"                    # LOW, MEDIUM, HIGH, CRITICAL
    first_congested_time: Optional[float] = None
    last_congested_time: Optional[float] = None
    congested_duration: float = 0.0
    evidence: List[str] = field(default_factory=list)
    recommendation: str = "Flow is normal."
    alert_start_time: Optional[float] = None


class ZoneAnalyticsEngine:
    """
    Zone dwell-time analytics & explainable bottleneck detection engine.

    Features:
    - Point-in-polygon ray casting with boundary grace-period hysteresis.
    - Timestamp-based elapsed dwell calculation (not fixed-FPS assumptions).
    - Real-time separation of active in-progress visits vs. completed visits.
    - Track interruption and graceful visit finalization.
    - Explainable bottleneck detection with persistence windows and recommendations.
    - Anonymous temporary tracking IDs only (zero biometrics).
    """

    def __init__(
        self,
        exit_grace_seconds: float = 2.0,
        track_expire_seconds: float = 5.0,
        bottleneck_persistence_seconds: float = 4.0,
    ):
        self._lock = threading.Lock()
        self._zones: Dict[str, Zone] = {}

        # Active visits: { (track_id, zone_id): DwellRecord }
        self._active: Dict[Tuple[int, str], DwellRecord] = {}

        # Pending exits for boundary hysteresis:
        # { (track_id, zone_id): {"candidate_exit_time": float, "record": DwellRecord} }
        self._pending_exits: Dict[Tuple[int, str], Dict[str, Any]] = {}

        # Completed visits: list of DwellRecord (bounded retention)
        self._completed: List[DwellRecord] = []
        self._max_completed = 1000

        # Unique tracks seen per zone
        self._unique_tracks_per_zone: Dict[str, Set[int]] = defaultdict(set)
        # Cumulative total entries per zone
        self._total_entries: Dict[str, int] = defaultdict(int)
        # Current active occupants per zone for immediate frame
        self._current_occupants: Dict[str, Set[int]] = defaultdict(set)

        # Zone-to-zone transition matrix: { (from_zone_id, to_zone_id): count }
        self._transitions: Dict[Tuple[str, str], int] = defaultdict(int)

        # Last known primary zone for each track_id
        self._last_zone: Dict[int, Optional[str]] = {}

        # Last seen store-wide timestamp per track_id
        self._track_last_seen: Dict[int, float] = {}

        # Rolling history of occupancy: { zone_id: deque of {"ts": float, "occupancy": int} }
        self._history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._max_history = 180

        # Bottleneck state per zone
        self._bottlenecks: Dict[str, BottleneckState] = defaultdict(BottleneckState)

        # Configuration parameters
        self.exit_grace_seconds = exit_grace_seconds
        self.track_expire_seconds = track_expire_seconds
        self.bottleneck_persistence_seconds = bottleneck_persistence_seconds

        # Store baseline dwell expectation defaults (in seconds)
        self.baseline_dwell_times = {
            "entrance": 30.0,
            "checkout": 120.0,
            "electronics": 180.0,
            "grocery": 120.0,
            "promo": 60.0,
            "display": 90.0,
            "aisle": 45.0,
            "restricted": 15.0,
            "default": 90.0,
        }

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
            self._bottlenecks.pop(zone_id, None)

    def get_zones(self) -> List[Zone]:
        with self._lock:
            return list(self._zones.values())

    def get_zone(self, zone_id: str) -> Optional[Zone]:
        with self._lock:
            return self._zones.get(zone_id)

    # ── Core Update Loop ──────────────────────────────────────────────

    def update(
        self,
        tracked_persons,
        frame_width: Optional[int] = None,
        frame_height: Optional[int] = None,
        timestamp: Optional[float] = None,
        **kwargs
    ):
        """
        Process one frame of tracked persons.
        - tracked_persons: iterable of objects having .track_id and .bottom_center
        - frame_width, frame_height: dimensions of input frame
        - timestamp: optional deterministic float timestamp (defaults to time.time())
        """
        w = max(1, frame_width or kwargs.get("frame_w") or 640)
        h = max(1, frame_height or kwargs.get("frame_h") or 480)
        now = timestamp if timestamp is not None else time.time()

        with self._lock:
            # Map of zone_id -> set of track IDs currently inside
            current_ids_in_zone: Dict[str, Set[int]] = {zid: set() for zid in self._zones}
            active_tids_in_frame: Set[int] = set()

            for person in tracked_persons:
                if person is None:
                    continue

                tid = getattr(person, 'track_id', None)
                if tid is None:
                    continue

                active_tids_in_frame.add(tid)
                self._track_last_seen[tid] = now

                # Extract bottom-center or center coordinates
                bc = getattr(person, 'bottom_center', None)
                if bc is None:
                    bc = getattr(person, 'center', None)
                if bc is None and hasattr(person, 'bbox') and len(person.bbox) >= 4:
                    bc = (int((person.bbox[0] + person.bbox[2]) / 2), int(person.bbox[3]))
                if bc is None:
                    continue

                bcx, bcy = bc
                fx = max(0.0, min(1.0, bcx / float(w)))
                fy = max(0.0, min(1.0, bcy / float(h)))

                person_zones = []
                for zid, zone in self._zones.items():
                    if zone.contains_point(fx, fy):
                        person_zones.append(zid)
                        current_ids_in_zone[zid].add(tid)
                        self._unique_tracks_per_zone[zid].add(tid)

                        key = (tid, zid)

                        # Check if this person had a pending exit — if so, cancel exit!
                        if key in self._pending_exits:
                            del self._pending_exits[key]

                        # If not already tracking active visit, initiate DwellRecord
                        if key not in self._active:
                            self._total_entries[zid] += 1
                            self._active[key] = DwellRecord(
                                track_id=tid,
                                zone_id=zid,
                                enter_time=now,
                                last_seen_time=now
                            )
                        else:
                            self._active[key].last_seen_time = now

                # Track zone transitions (primary zone is first matched zone)
                primary_zone = person_zones[0] if person_zones else None
                prev_zone = self._last_zone.get(tid)

                if primary_zone is not None:
                    if prev_zone is not None and prev_zone != primary_zone:
                        self._transitions[(prev_zone, primary_zone)] += 1
                    self._last_zone[tid] = primary_zone

            # 1. Handle abandoned/expired tracks (person vanished from camera view entirely)
            expired_tids = [
                tid for tid, last_seen in self._track_last_seen.items()
                if (now - last_seen) > self.track_expire_seconds
            ]
            for exp_tid in expired_tids:
                exp_keys = [k for k in self._active.keys() if k[0] == exp_tid]
                for key in exp_keys:
                    rec = self._active.pop(key, None)
                    if rec:
                        rec.exit_time = rec.last_seen_time
                        rec.interrupted = True
                        self._completed.append(rec)
                        if len(self._completed) > self._max_completed:
                            self._completed = self._completed[-self._max_completed:]
                self._last_zone.pop(exp_tid, None)
                self._track_last_seen.pop(exp_tid, None)
                # Clear from pending exits
                pending_keys = [k for k in self._pending_exits.keys() if k[0] == exp_tid]
                for k in pending_keys:
                    self._pending_exits.pop(k, None)

            # 2. Handle zone exits with grace-period hysteresis (for tracks still on camera)
            current_frame_track_ids = active_tids_in_frame
            active_keys = list(self._active.keys())
            for (tid, zid) in active_keys:
                record = self._active[(tid, zid)]
                is_currently_inside = tid in current_ids_in_zone.get(zid, set())

                if not is_currently_inside:
                    key = (tid, zid)
                    # Only treat as boundary exit if track is visible elsewhere on camera
                    if tid in current_frame_track_ids:
                        if key not in self._pending_exits:
                            # Place in pending exit state
                            self._pending_exits[key] = {
                                "candidate_exit_time": now,
                                "record": record
                            }
                        else:
                            # Check if grace period has expired
                            candidate_exit_time = self._pending_exits[key]["candidate_exit_time"]
                            if (now - candidate_exit_time) >= self.exit_grace_seconds:
                                record.exit_time = candidate_exit_time
                                self._completed.append(record)
                                del self._active[key]
                                del self._pending_exits[key]

                                if len(self._completed) > self._max_completed:
                                    self._completed = self._completed[-self._max_completed:]

            # Record current occupants and occupancy history, and run bottleneck evaluations
            self._current_occupants = defaultdict(set)
            for zid, zone in self._zones.items():
                zone_occupants = current_ids_in_zone.get(zid, set())
                self._current_occupants[zid] = set(zone_occupants)
                current_occ = len(zone_occupants)
                self._history[zid].append({"ts": now, "occupancy": current_occ})
                if len(self._history[zid]) > self._max_history:
                    self._history[zid] = self._history[zid][-self._max_history:]

                # Update bottleneck state for this zone
                self._evaluate_bottleneck(zid, zone, current_occ, now)

    # ── Bottleneck Detection ──────────────────────────────────────────

    def _evaluate_bottleneck(self, zid: str, zone: Zone, current_occ: int, now: float):
        """
        Evaluate explainable bottleneck criteria with persistence windows and hysteresis.
        """
        b_state = self._bottlenecks[zid]
        capacity = max(zone.capacity, 1)
        occ_ratio = current_occ / float(capacity)

        # Active visits in this zone
        active_records = [r for (tid, z_id), r in self._active.items() if z_id == zid]
        active_dwells = [r.dwell_seconds(now) for r in active_records]
        long_dwell_active = [d for d in active_dwells if d >= zone.dwell_alert_seconds]

        # Evidence accumulation
        evidence: List[str] = []
        is_congested_instant = False

        if occ_ratio >= 1.2:
            is_congested_instant = True
            evidence.append(f"Capacity exceeded: {current_occ}/{capacity} ({int(occ_ratio * 100)}%)")
        elif occ_ratio >= zone.congestion_threshold_ratio:
            is_congested_instant = True
            evidence.append(f"Near capacity: {current_occ}/{capacity} ({int(occ_ratio * 100)}%)")

        if len(long_dwell_active) >= 2:
            is_congested_instant = True
            evidence.append(f"{len(long_dwell_active)} visitors dwelling > {zone.dwell_alert_seconds:.0f}s threshold")

        # Persistence calculation
        if is_congested_instant:
            b_state.last_congested_time = now
            if b_state.first_congested_time is None:
                b_state.first_congested_time = now
            b_state.congested_duration = max(0.0, now - b_state.first_congested_time)
        else:
            # Decay or reset persistence when condition clears for >= 1.5s
            if b_state.last_congested_time is not None:
                if (now - b_state.last_congested_time) >= 1.5:
                    b_state.first_congested_time = None
                    b_state.last_congested_time = None
                    b_state.congested_duration = 0.0
            else:
                b_state.first_congested_time = None
                b_state.congested_duration = 0.0

        # Determine severity and state based on duration and load
        duration = b_state.congested_duration
        if duration >= self.bottleneck_persistence_seconds and is_congested_instant:
            b_state.is_bottleneck = True
            if b_state.alert_start_time is None:
                b_state.alert_start_time = b_state.first_congested_time

            if occ_ratio >= 1.5 or (occ_ratio >= 1.2 and len(long_dwell_active) >= 3):
                b_state.severity = "CRITICAL"
                recommendation = f"Immediate staff intervention required at {zone.name}. Congestion sustained for {duration:.1f}s."
            elif occ_ratio >= 1.0 or len(long_dwell_active) >= 2:
                b_state.severity = "HIGH"
                recommendation = f"Deploy staff to assist customer flow at {zone.name} ({duration:.1f}s sustained load)."
            else:
                b_state.severity = "MEDIUM"
                recommendation = f"Monitor {zone.name} closely. Approaching bottleneck threshold."

            evidence.append(f"Sustained for {duration:.1f}s (threshold: {self.bottleneck_persistence_seconds:.1f}s)")
            b_state.evidence = evidence
            b_state.recommendation = recommendation
        else:
            if not is_congested_instant and (b_state.last_congested_time is None or (now - b_state.last_congested_time) >= 1.5):
                b_state.is_bottleneck = False
                b_state.severity = "LOW"
                b_state.alert_start_time = None
                b_state.evidence = ["Normal browsing flow"] if current_occ > 0 else ["Zone empty"]
                b_state.recommendation = "Flow is normal. No intervention needed."

    # ── Statistics & Reporting ────────────────────────────────────────

    def get_zone_stats(self, current_time: Optional[float] = None) -> Dict[str, Dict[str, Any]]:
        """
        Compute comprehensive dwell-time, occupancy, and bottleneck metrics for all zones.
        Separates active real-time visit statistics from completed visit aggregates.
        """
        now = current_time if current_time is not None else time.time()
        with self._lock:
            result = {}

            for zid, zone in self._zones.items():
                completed = [r for r in self._completed if r.zone_id == zid]
                active_pairs = [
                    (k, r) for k, r in self._active.items()
                    if k[1] == zid and k not in self._pending_exits
                ]
                active_records = [r for (k, r) in active_pairs]


                # Active visits dwell durations
                active_dwells = [r.dwell_seconds(now) for r in active_records]
                avg_active_dwell = sum(active_dwells) / len(active_dwells) if active_dwells else 0.0
                max_active_dwell = max(active_dwells) if active_dwells else 0.0

                # Completed visits dwell durations
                completed_dwells = [r.dwell_seconds(now) for r in completed if r.dwell_seconds(now) > 0]
                avg_completed_dwell = sum(completed_dwells) / len(completed_dwells) if completed_dwells else 0.0
                median_completed_dwell = (
                    statistics.median(completed_dwells)
                    if len(completed_dwells) >= 2
                    else avg_completed_dwell
                )
                max_completed_dwell = max(completed_dwells) if completed_dwells else 0.0

                # P90 completed dwell
                if len(completed_dwells) >= 10:
                    sorted_d = sorted(completed_dwells)
                    p90_idx = int(0.9 * len(sorted_d))
                    p90_dwell = sorted_d[p90_idx]
                else:
                    p90_dwell = max_completed_dwell

                current_occupancy = len(self._current_occupants.get(zid, set()))
                unique_visitors = len(self._unique_tracks_per_zone[zid])
                total_entries = self._total_entries[zid]

                congestion_pct = (current_occupancy / max(zone.capacity, 1)) * 100.0
                congestion_status = (
                    "CRITICAL" if congestion_pct >= 100 else
                    "HIGH" if congestion_pct >= 75 else
                    "MEDIUM" if congestion_pct >= 50 else
                    "LOW"
                )

                # Dwell alert evaluation (considers active and completed)
                long_dwell_active = [d for d in active_dwells if d >= zone.dwell_alert_seconds]
                dwell_alert = (
                    (avg_completed_dwell > zone.dwell_alert_seconds and len(completed_dwells) >= 3) or
                    (len(long_dwell_active) >= 2)
                )

                b_state = self._bottlenecks[zid]
                history = self._history.get(zid, [])[-60:]

                result[zid] = {
                    "zone_id": zid,
                    "zone_name": zone.name,
                    "zone_type": zone.type,
                    "current_occupancy": current_occupancy,
                    "capacity": zone.capacity,
                    "unique_visitors": unique_visitors,
                    "total_entries": total_entries,
                    "total_completed_visits": len(completed),
                    # Dwell statistics
                    "avg_dwell_seconds": round(avg_completed_dwell, 1),
                    "median_dwell_seconds": round(median_completed_dwell, 1),
                    "max_dwell_seconds": round(max(max_completed_dwell, max_active_dwell), 1),
                    "p90_dwell_seconds": round(p90_dwell, 1),
                    "active_avg_dwell_seconds": round(avg_active_dwell, 1),
                    "active_max_dwell_seconds": round(max_active_dwell, 1),
                    "sample_count": len(completed_dwells),
                    # Congestion & Alerts
                    "congestion_pct": round(congestion_pct, 1),
                    "congestion_status": congestion_status,
                    "congestion_level": congestion_status,
                    "dwell_alert": dwell_alert,
                    "long_dwell_active_count": len(long_dwell_active),
                    # Bottleneck detection
                    "bottleneck": {
                        "is_bottleneck": b_state.is_bottleneck,
                        "severity": b_state.severity,
                        "congested_duration_seconds": round(b_state.congested_duration, 1),
                        "evidence": b_state.evidence,
                        "recommendation": b_state.recommendation,
                        "thresholds": {
                            "capacity": zone.capacity,
                            "dwell_alert_seconds": zone.dwell_alert_seconds,
                            "congestion_ratio": zone.congestion_threshold_ratio,
                            "persistence_window_seconds": self.bottleneck_persistence_seconds
                        }
                    },
                    "history": history,
                }

            return result

    def get_bottleneck_summary(self) -> Dict[str, Any]:
        """Aggregate summary of active bottlenecks across all store zones."""
        stats = self.get_zone_stats()
        active_bottlenecks = []
        for zid, s in stats.items():
            b = s["bottleneck"]
            if b["is_bottleneck"] or b["severity"] in ("HIGH", "CRITICAL"):
                active_bottlenecks.append({
                    "zone_id": zid,
                    "zone_name": s["zone_name"],
                    "zone_type": s["zone_type"],
                    "severity": b["severity"],
                    "duration_seconds": b["congested_duration_seconds"],
                    "evidence": b["evidence"],
                    "recommendation": b["recommendation"]
                })

        return {
            "total_bottlenecks": len(active_bottlenecks),
            "status": "CONGESTED" if any(b["severity"] == "CRITICAL" for b in active_bottlenecks)
                      else ("WARNING" if active_bottlenecks else "SMOOTH"),
            "bottlenecks": active_bottlenecks,
        }

    def get_transitions(self) -> Dict[str, Any]:
        """
        Zone-to-zone customer routing counts and normalized transition probabilities.
        Computes P(destination | origin) = count(origin -> dest) / total_exits(origin).
        """
        with self._lock:
            # Calculate total outflows per origin zone
            outflow: Dict[str, int] = defaultdict(int)
            for (from_z, _), count in self._transitions.items():
                outflow[from_z] += count

            total_transitions = sum(self._transitions.values())
            data_sufficient = total_transitions >= 5

            transitions = []
            matrix: Dict[str, Dict[str, Any]] = defaultdict(dict)

            # Pre-populate matrix for all known zones
            all_zone_ids = list(self._zones.keys())
            for z1 in all_zone_ids:
                for z2 in all_zone_ids:
                    matrix[z1][z2] = {"count": 0, "probability": 0.0}

            for (from_z, to_z), count in self._transitions.items():
                from_total = outflow.get(from_z, 1)
                prob = round(count / from_total, 3) if from_total > 0 else 0.0
                transitions.append({
                    "from_zone": from_z,
                    "to_zone": to_z,
                    "count": count,
                    "probability": prob,
                })
                if from_z in matrix and to_z in matrix[from_z]:
                    matrix[from_z][to_z] = {"count": count, "probability": prob}

            confidence = "HIGH" if total_transitions >= 20 else ("MEDIUM" if total_transitions >= 5 else "LOW")

            return {
                "transitions": sorted(transitions, key=lambda x: -x["count"]),
                "matrix": dict(matrix),
                "zone_outflow": dict(outflow),
                "total_transitions": total_transitions,
                "data_sufficient": data_sufficient,
                "confidence": confidence,
                "disclaimer": (
                    "Observed anonymous movement transitions only. "
                    "Requires multiple visits to establish stable routing probabilities."
                ),
            }

    def get_movement_data(self) -> Dict[str, Any]:
        """Aggregated movement data."""
        return self.get_transitions()

    def reset(self):
        """Reset all state counters and tracking tables."""
        with self._lock:
            self._active.clear()
            self._pending_exits.clear()
            self._completed.clear()
            self._unique_tracks_per_zone.clear()
            self._transitions.clear()
            self._last_zone.clear()
            self._track_last_seen.clear()
            self._history.clear()
            self._bottlenecks.clear()

    # ── Default Zones ─────────────────────────────────────────────────

    @staticmethod
    def default_zones() -> List[Zone]:
        """Return standardized retail zones for StorePulse AI."""
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


# Singleton instance
zone_analytics_engine = ZoneAnalyticsEngine()
