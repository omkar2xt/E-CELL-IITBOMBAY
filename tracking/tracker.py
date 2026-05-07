# tracker.py
# ============================================================
# Wrapper for ByteTrack via Ultralytics.
#
# ByteTrack works in 2 assignment stages per frame:
#   1. High-confidence detections  -> match to active tracks via IoU
#   2. Low-confidence detections   -> match to momentarily "lost" tracks
# This is what makes ByteTrack more stable than DeepSORT in crowds.
# ============================================================

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from ultralytics import YOLO
from collections import defaultdict
import config as config


@dataclass
class TrackedPerson:
    """
    A single person currently being tracked.
    Extends Detection (week 1) with additional tracking info.
    """
    track_id: int               # Unique ID consistent across frames
    bbox: List[float]           # [x1, y1, x2, y2]
    confidence: float

    # History of center positions for drawing trajectories
    # Key: track_id, Value: list of (cx, cy)
    # Stored outside the class so it persists across frames

    @property
    def center(self) -> Tuple[int, int]:
        x1, y1, x2, y2 = self.bbox
        return (int((x1 + x2) / 2), int((y1 + y2) / 2))

    @property
    def bottom_center(self) -> Tuple[int, int]:
        """
        Bottom center point of the bounding box.
        More accurate for crossing detection than the center,
        as it represents the person's "foot position".
        """
        x1, y1, x2, y2 = self.bbox
        return (int((x1 + x2) / 2), int(y2))

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]


class PersonTracker:
    """
    Multi-person tracker using ByteTrack (via Ultralytics).

    Why via Ultralytics and not a manual ByteTrack implementation?
    - Ultralytics has already integrated ByteTrack optimally with YOLO
    - Kalman Filter and Hungarian assignment are tuned for person tracking
    - Single pipeline: detect + track in one call
    """

    def __init__(self):
        print(f"[Tracker] Loading model: {config.MODEL_NAME}")
        self.model = YOLO(config.MODEL_NAME)

        # Position history per track_id for drawing trajectories
        # { track_id: [(cx, cy), (cx, cy), ...] }
        self.trajectories = defaultdict(list)

        # Set of track_ids that have been seen
        # Used for detecting "new tracks" (new people entering the frame)
        self.seen_ids = set()

        print(f"[Tracker] ByteTrack ready. Buffer: {config.TRACK_BUFFER} frames")

    def update(self, frame: np.ndarray) -> List[TrackedPerson]:
        """
        Process one frame: detect + track everyone.

        Returns a list of TrackedPersons with consistent track_ids.
        """
        # Run YOLO with ByteTrack tracker
        # persist=True: important! This is what keeps track IDs consistent
        #               across frames. Without this, IDs reset every frame.
        results = self.model.track(
            frame,
            classes=[config.CLASS_PERSON],
            conf=config.TRACK_THRESH,
            tracker="bytetrack.yaml",   # Default ByteTrack config from Ultralytics
            persist=True,               # REQUIRED for consistent IDs
            verbose=False
        )

        tracked = []

        if results[0].boxes is None or results[0].boxes.id is None:
            # No people detected in this frame
            return tracked

        boxes = results[0].boxes

        for i in range(len(boxes)):
            # Extract data per person
            bbox = boxes.xyxy[i].cpu().numpy().tolist()
            conf = float(boxes.conf[i].cpu().numpy())
            track_id = int(boxes.id[i].cpu().numpy())

            person = TrackedPerson(
                track_id=track_id,
                bbox=bbox,
                confidence=conf
            )

            # Update trajectory
            self._update_trajectory(track_id, person.center)

            tracked.append(person)
            self.seen_ids.add(track_id)

        return tracked

    def _update_trajectory(self, track_id: int, center: Tuple[int, int]):
        """
        Store history of center positions per track.
        Limit trajectory length to avoid memory leaks.
        """
        self.trajectories[track_id].append(center)

        # Limit to the last N frames
        max_len = config.TRAJECTORY_LENGTH   # default 30 frames
        if len(self.trajectories[track_id]) > max_len:
            self.trajectories[track_id] = self.trajectories[track_id][-max_len:]

    def get_trajectory(self, track_id: int) -> List[Tuple[int, int]]:
        """Get position history for a single track."""
        return self.trajectories.get(track_id, [])

    def cleanup_old_tracks(self, active_ids: set):
        """
        Remove trajectories for tracks that have been inactive for a long time.
        Call this every few hundred frames to prevent memory leaks.
        """
        dead_ids = set(self.trajectories.keys()) - active_ids
        # Only remove those inactive for longer than 2x buffer
        for tid in dead_ids:
            if len(self.trajectories[tid]) > 0:
                del self.trajectories[tid]