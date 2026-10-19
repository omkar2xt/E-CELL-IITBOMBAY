# counter.py
# ============================================================
# StorePulse AI — Robust Virtual Line Crossing & Occupancy Counter
#
# Features:
# 1. Segment-bounded crossing detection (verifies position along line length).
# 2. Strict directional verification (direction vector from trajectory).
# 3. Single-event guarantee per person/visit (no duplicate counts across frames).
# 4. Anti-jitter hysteresis dead zone + re-crossing cooldown protection.
# 5. Full handling of people already inside at startup (initial_occupancy).
# 6. Safe tracker lifecycle management (stale ID pruning and reset).
# ============================================================

import time
from typing import Dict, Tuple, List, Set, Optional
from collections import deque
from dataclasses import dataclass, field

try:
    from tracking.tracker import TrackedPerson
    from tracking import config
except ImportError:
    try:
        from tracker import TrackedPerson
        import config
    except ImportError:
        TrackedPerson = None
        config = None


@dataclass
class PersonTrackState:
    """State management for a single tracked person."""
    last_side: str                       # "A", "B", "ZONE", or "OUT_OF_BOUNDS"
    has_entered: bool = False            # True once person has entered store
    has_exited: bool = False             # True once person has exited store
    last_crossing_frame: int = -999      # Frame index of last crossing event
    last_crossing_time: float = 0.0      # Timestamp of last crossing event
    last_crossing_dir: Optional[str] = None  # "IN" or "OUT"
    positions: deque = field(default_factory=lambda: deque(maxlen=20))


class LineCounter:
    """
    Counts people crossing a virtual line with robust duplicate suppression,
    re-crossing cooldowns, direction verification, and occupancy tracking.
    """

    def __init__(
        self,
        line_start: Tuple[int, int],
        line_end: Tuple[int, int],
        orientation: Optional[str] = None,
        tolerance: Optional[int] = None,
        initial_occupancy: int = 0,
        re_crossing_cooldown_frames: int = 2,
        re_crossing_cooldown_seconds: float = 0.0,
        segment_margin: int = 40,
    ):
        self.line_start = line_start
        self.line_end = line_end
        self.orientation = (
            orientation
            if orientation is not None
            else getattr(config, 'LINE_ORIENTATION', 'horizontal')
        )
        self.tolerance = (
            tolerance
            if tolerance is not None
            else getattr(config, 'LINE_CROSSING_TOLERANCE', 5)
        )
        self.initial_occupancy = max(0, initial_occupancy)
        self.re_crossing_cooldown_frames = re_crossing_cooldown_frames
        self.re_crossing_cooldown_seconds = re_crossing_cooldown_seconds
        self.segment_margin = segment_margin

        # Counters
        self.count_in = 0
        self.count_out = 0
        self.frame_count = 0

        # Detailed tracking state per track_id
        self._states: Dict[int, PersonTrackState] = {}

        # List of crossing events in this frame (track_id, direction)
        self.current_crossings: List[Tuple[int, str]] = []

    @property
    def _track_states(self) -> Dict[int, str]:
        """Backward-compatibility mapping {track_id: side}."""
        return {tid: state.last_side for tid, state in self._states.items()}

    def set_initial_occupancy(self, count: int):
        """Set initial occupancy for people already present at startup."""
        self.initial_occupancy = max(0, int(count))

    def update(self, tracked_persons: List[TrackedPerson], timestamp: Optional[float] = None):
        """
        Process all people in this frame.
        Update counts if verified crossings occur.
        """
        self.frame_count += 1
        self.current_crossings = []
        now = timestamp if timestamp is not None else time.time()

        for person in tracked_persons:
            if person is None:
                continue
            self._check_crossing(person, now)

    def _get_side(self, point: Tuple[int, int]) -> str:
        """
        Determine which side of the line the point is on.
        Returns:
            "A": Left of vertical line (or above horizontal line).
            "B": Right of vertical line (or below horizontal line).
            "ZONE": Within the dead zone (+/- tolerance).
            "OUT_OF_BOUNDS": Beyond the line segment's span.
        """
        px, py = point

        if self.orientation == "horizontal":
            # Vertical line, x = line_x
            line_x = self.line_start[0]
            y_min = min(self.line_start[1], self.line_end[1])
            y_max = max(self.line_start[1], self.line_end[1])

            # Check segment boundaries along the Y axis
            if y_max > y_min:
                if py < (y_min - self.segment_margin) or py > (y_max + self.segment_margin):
                    return "OUT_OF_BOUNDS"

            # Check position relative to X line
            if px < line_x - self.tolerance:
                return "A"
            elif px > line_x + self.tolerance:
                return "B"
            else:
                return "ZONE"
        else:
            # Horizontal line, y = line_y
            line_y = self.line_start[1]
            x_min = min(self.line_start[0], self.line_end[0])
            x_max = max(self.line_start[0], self.line_end[0])

            # Check segment boundaries along the X axis
            if x_max > x_min:
                if px < (x_min - self.segment_margin) or px > (x_max + self.segment_margin):
                    return "OUT_OF_BOUNDS"

            # Check position relative to Y line
            if py < line_y - self.tolerance:
                return "A"
            elif py > line_y + self.tolerance:
                return "B"
            else:
                return "ZONE"

    def _check_crossing(self, person: TrackedPerson, now: float):
        """
        Check if person crossed the line in a verified entry or exit direction.
        Applies cooldown, vector direction, and duplicate suppression.
        """
        tid = person.track_id
        point = person.bottom_center
        current_side = self._get_side(point)

        # Ignore points in dead zone or completely out of segment bounds
        if current_side in ("ZONE", "OUT_OF_BOUNDS"):
            if tid in self._states:
                self._states[tid].positions.append(point)
            return

        # New track initialization
        if tid not in self._states:
            # If person starts on side A (inside the store), mark has_entered=True so they are
            # accounted for as an existing occupant and do not trigger a false "IN" crossing.
            initial_entered = (current_side == "A")
            self._states[tid] = PersonTrackState(
                last_side=current_side,
                has_entered=initial_entered,
                has_exited=False,
                positions=deque([point], maxlen=20)
            )
            return

        state = self._states[tid]
        prev_side = state.last_side
        state.positions.append(point)

        # Crossing candidate: side changed from A -> B or B -> A
        if prev_side in ("A", "B") and prev_side != current_side:
            # Calculate directional movement vector dx, dy
            dx = 0
            dy = 0
            if len(state.positions) >= 2:
                p_old = state.positions[-2]
                p_new = state.positions[-1]
                dx = p_new[0] - p_old[0]
                dy = p_new[1] - p_old[1]

            frames_since_crossing = self.frame_count - state.last_crossing_frame
            time_since_crossing = now - state.last_crossing_time if state.last_crossing_time > 0 else 999.0

            # Cooldown check to prevent bouncing / jitter on consecutive frames
            cooldown_active = (
                frames_since_crossing < self.re_crossing_cooldown_frames
                or (self.re_crossing_cooldown_seconds > 0 and time_since_crossing < self.re_crossing_cooldown_seconds)
            )

            if self.orientation == "horizontal":
                # Vertical line:
                # B -> A = moving LEFT = IN (dx <= 0)
                # A -> B = moving RIGHT = OUT (dx >= 0)
                if prev_side == "B" and current_side == "A":
                    # Direction verification: moving leftwards
                    if dx <= 0 and not cooldown_active:
                        if not state.has_entered:
                            self.count_in += 1
                            state.has_entered = True
                            state.has_exited = False
                            state.last_crossing_frame = self.frame_count
                            state.last_crossing_time = now
                            state.last_crossing_dir = "IN"
                            self.current_crossings.append((tid, "IN"))

                elif prev_side == "A" and current_side == "B":
                    # Direction verification: moving rightwards
                    if dx >= 0 and not cooldown_active:
                        if not state.has_exited:
                            self.count_out += 1
                            state.has_exited = True
                            state.has_entered = False
                            state.last_crossing_frame = self.frame_count
                            state.last_crossing_time = now
                            state.last_crossing_dir = "OUT"
                            self.current_crossings.append((tid, "OUT"))

            else:
                # Horizontal line:
                # A -> B = moving DOWN = IN (dy >= 0)
                # B -> A = moving UP = OUT (dy <= 0)
                if prev_side == "A" and current_side == "B":
                    if dy >= 0 and not cooldown_active:
                        if not state.has_entered:
                            self.count_in += 1
                            state.has_entered = True
                            state.has_exited = False
                            state.last_crossing_frame = self.frame_count
                            state.last_crossing_time = now
                            state.last_crossing_dir = "IN"
                            self.current_crossings.append((tid, "IN"))

                elif prev_side == "B" and current_side == "A":
                    if dy <= 0 and not cooldown_active:
                        if not state.has_exited:
                            self.count_out += 1
                            state.has_exited = True
                            state.has_entered = False
                            state.last_crossing_frame = self.frame_count
                            state.last_crossing_time = now
                            state.last_crossing_dir = "OUT"
                            self.current_crossings.append((tid, "OUT"))

            # Update last side
            state.last_side = current_side

    @property
    def current_occupancy(self) -> int:
        """
        Current store occupancy calculated consistently from initial occupancy
        and verified net entry/exit events.
        """
        return max(0, self.initial_occupancy + self.count_in - self.count_out)

    def has_crossing_this_frame(self) -> bool:
        """Returns True if any crossing occurred in the current frame."""
        return len(self.current_crossings) > 0

    def reset_counts(self, initial_occupancy: int = 0):
        """Reset counters and session state for a new session or video loop."""
        self.count_in = 0
        self.count_out = 0
        self.frame_count = 0
        self.initial_occupancy = max(0, int(initial_occupancy))
        self._states.clear()
        self.current_crossings.clear()

    def cleanup_old_tracks(self, active_ids: Set[int]):
        """
        Prune state for terminated tracks to prevent memory leaks and track ID pollution.
        """
        if len(self._states) > 500:
            stale_ids = [
                tid for tid in self._states
                if tid not in active_ids and (self.frame_count - self._states[tid].last_crossing_frame) > 150
            ]
            for tid in stale_ids[:250]:
                self._states.pop(tid, None)
