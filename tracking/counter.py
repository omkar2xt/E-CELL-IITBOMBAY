# counter.py
# ============================================================
# Virtual line crossing counter.
#
# How it works:
# 1. Define a virtual line in the frame (e.g., at an entrance)
# 2. Every frame, check the position of each tracked person against the line
# 3. If someone moves from one side to the other -> crossing
# 4. The direction of the crossing determines IN or OUT
#
# Why use bottom_center instead of center?
# A person's feet are a more stable position reference.
# If using the center, a person bending over could trigger a false crossing.
# ============================================================

from typing import Dict, Tuple, List, Set, Optional

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


class LineCounter:
    """
    Counts people crossing a virtual line.

    State per track_id:
    - "side": which side the person was last seen on (A or B)
    - When the side changes -> crossing occurs
    """

    def __init__(
        self,
        line_start: Tuple[int, int],
        line_end: Tuple[int, int],
        orientation: Optional[str] = None,
        tolerance: Optional[int] = None,
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

        # Counter
        self.count_in = 0
        self.count_out = 0

        # Last known state for each track: {"side": "A" or "B"}
        # "A" = left/above the line
        # "B" = right/below the line
        self._track_states: Dict[int, str] = {}

        # List of crossing events in this frame (for visual flash)
        # Format: (track_id, direction)  direction = "IN" or "OUT"
        self.current_crossings: List[Tuple[int, str]] = []


    def update(self, tracked_persons: List[TrackedPerson]):
        """
        Process all people in this frame.
        Update the counter if anyone crosses.
        """
        self.current_crossings = []  # reset events per frame

        for person in tracked_persons:
            self._check_crossing(person)

    def _get_side(self, point: Tuple[int, int]) -> str:
        """
        Determine which side the point is on relative to the line.
        Returns "A" or "B".

        For a horizontal line (LINE_ORIENTATION = "vertical"):
            A = above the line (y < line_y)
            B = below the line (y > line_y)

        For a vertical line (LINE_ORIENTATION = "horizontal"):
            A = left of the line (x < line_x)
            B = right of the line (x > line_x)
        """
        px, py = point

        if self.orientation == "horizontal":
            # Vertical line, people moving left-right
            line_x = self.line_start[0]
            if px < line_x - self.tolerance:
                return "A"
            elif px > line_x + self.tolerance:
                return "B"
            else:
                return "ZONE"  # Inside dead zone, not counted
        else:
            # Horizontal line, people moving up-down
            line_y = self.line_start[1]
            if py < line_y - self.tolerance:
                return "A"
            elif py > line_y + self.tolerance:
                return "B"
            else:
                return "ZONE"

    def _check_crossing(self, person: TrackedPerson):
        """
        Check if this person has just crossed the line.
        """
        tid = person.track_id
        point = person.bottom_center
        current_side = self._get_side(point)

        # Skip if in the dead zone
        if current_side == "ZONE":
            return

        # If it's a new track (not in state yet), save initial position
        if tid not in self._track_states:
            self._track_states[tid] = current_side
            return

        prev_side = self._track_states[tid]

        # Crossing occurs if the side changes
        if prev_side != current_side:
            if self.orientation == "horizontal":
                # Vertical line: A=left, B=right
                # B -> A = moving left  = IN (from right to left)
                # A -> B = moving right = OUT (from left to right)
                if prev_side == "B" and current_side == "A":
                    self.count_in += 1
                    self.current_crossings.append((tid, "IN"))
                elif prev_side == "A" and current_side == "B":
                    self.count_out += 1
                    self.current_crossings.append((tid, "OUT"))
            else:
                # Horizontal line: A=up, B=down
                # A -> B = moving down = IN
                # B -> A = moving up   = OUT
                if prev_side == "A" and current_side == "B":
                    self.count_in += 1
                    self.current_crossings.append((tid, "IN"))
                elif prev_side == "B" and current_side == "A":
                    self.count_out += 1
                    self.current_crossings.append((tid, "OUT"))

            # Update state
            self._track_states[tid] = current_side

    @property
    def current_occupancy(self) -> int:
        """
        Estimate the number of people currently inside the area.
        IN - OUT. Can be negative if the video didn't start from the beginning
        or if someone exits without being recorded entering.
        """
        return max(0, self.count_in - self.count_out)

    def has_crossing_this_frame(self) -> bool:
        return len(self.current_crossings) > 0

    def reset_counts(self):
        """Reset counters (e.g., for hourly reports)."""
        self.count_in = 0
        self.count_out = 0
        self._track_states.clear()
        self.current_crossings.clear()

    def cleanup_old_tracks(self, active_ids: Set[int]):
        """
        Prune states for tracks that have terminated.
        Retains active track states while preventing memory leak.
        """
        # If track states grow large, keep only active and recent ones
        if len(self._track_states) > 1000:
            stale_ids = set(self._track_states.keys()) - active_ids
            # Remove up to 500 oldest stale IDs
            for tid in list(stale_ids)[:500]:
                self._track_states.pop(tid, None)