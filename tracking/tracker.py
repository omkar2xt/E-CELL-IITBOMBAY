# tracker.py
# ============================================================
# Wrapper for ByteTrack via Ultralytics for StorePulse AI.
#
# ByteTrack works in 2 assignment stages per frame:
#   1. High-confidence detections  -> match to active tracks via IoU
#   2. Low-confidence detections   -> match to momentarily "lost" tracks
# This is what makes ByteTrack more stable than DeepSORT in crowds.
# ============================================================

import sys
import os
import logging
from typing import List, Optional, Tuple, Set, Dict
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np

try:
    from tracking import config
except ImportError:
    import config

logger = logging.getLogger(__name__)


@dataclass
class TrackedPerson:
    """
    A single person currently being tracked.
    Extends person detection with persistent ID and tracking telemetry.
    """
    track_id: int               # Unique ID consistent across frames
    bbox: List[float]           # [x1, y1, x2, y2]
    confidence: float

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
        return max(0.0, float(self.bbox[2] - self.bbox[0]))

    @property
    def height(self) -> float:
        return max(0.0, float(self.bbox[3] - self.bbox[1]))


class PersonTracker:
    """
    Multi-person tracker using ByteTrack (via Ultralytics).
    Maintains temporary track IDs across frames with Kalman filter and IoU association.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        track_thresh: Optional[float] = None,
        match_thresh: Optional[float] = None,
        track_buffer: Optional[int] = None,
    ):
        self.model_name = model_name or getattr(config, 'MODEL_NAME', 'yolo11n.pt')
        self.track_thresh = (
            track_thresh
            if track_thresh is not None
            else getattr(config, 'TRACK_THRESH', 0.4)
        )
        self.match_thresh = (
            match_thresh
            if match_thresh is not None
            else getattr(config, 'MATCH_THRESH', 0.8)
        )
        self.track_buffer = (
            track_buffer
            if track_buffer is not None
            else getattr(config, 'TRACK_BUFFER', 30)
        )

        print(f"[Tracker] Loading model: {self.model_name}")
        from ultralytics import YOLO
        self.model = YOLO(self.model_name)

        # Position history per track_id for drawing trajectories
        self.trajectories: Dict[int, List[Tuple[int, int]]] = defaultdict(list)

        # Track metadata for lifecycle management
        self.last_seen_frame: Dict[int, int] = {}
        self.seen_ids: Set[int] = set()
        self.frame_count: int = 0

        print(f"[Tracker] ByteTrack ready. Buffer: {self.track_buffer} frames, Thresh: {self.track_thresh}")

    def update(self, frame: np.ndarray) -> List[TrackedPerson]:
        """
        Process one frame: detect + track everyone.
        Returns a list of TrackedPersons with consistent temporary track_ids.
        """
        self.frame_count += 1
        tracked: List[TrackedPerson] = []

        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0 or len(frame.shape) < 3:
            return tracked

        h, w = frame.shape[:2]
        if h <= 0 or w <= 0:
            return tracked

        try:
            # Run YOLO with ByteTrack tracker
            results = self.model.track(
                frame,
                classes=[getattr(config, 'CLASS_PERSON', 0)],
                conf=self.track_thresh,
                tracker="bytetrack.yaml",
                persist=True,
                verbose=False
            )
        except Exception as e:
            logger.error(f"[Tracker] Model tracking error on frame {self.frame_count}: {e}")
            return tracked

        if not results or len(results) == 0:
            return tracked

        first_res = results[0]
        if first_res.boxes is None or first_res.boxes.id is None:
            # No people tracked in this frame
            return tracked

        boxes = first_res.boxes

        for i in range(len(boxes)):
            try:
                raw_bbox = boxes.xyxy[i].cpu().numpy().tolist()
                conf = float(boxes.conf[i].cpu().numpy())
                track_id = int(boxes.id[i].cpu().numpy())

                # Validate coordinates within frame
                x1 = max(0.0, min(float(w), float(raw_bbox[0])))
                y1 = max(0.0, min(float(h), float(raw_bbox[1])))
                x2 = max(x1, min(float(w), float(raw_bbox[2])))
                y2 = max(y1, min(float(h), float(raw_bbox[3])))

                person = TrackedPerson(
                    track_id=track_id,
                    bbox=[x1, y1, x2, y2],
                    confidence=conf
                )

                # Update trajectory and timestamp
                self._update_trajectory(track_id, person.center)
                self.last_seen_frame[track_id] = self.frame_count
                self.seen_ids.add(track_id)

                tracked.append(person)
            except Exception as e:
                logger.debug(f"[Tracker] Error processing tracked box {i}: {e}")
                continue

        return tracked

    def _update_trajectory(self, track_id: int, center: Tuple[int, int]):
        """
        Store history of center positions per track.
        Limit trajectory length to avoid memory leaks.
        """
        self.trajectories[track_id].append(center)
        max_len = getattr(config, 'TRAJECTORY_LENGTH', 30)
        if len(self.trajectories[track_id]) > max_len:
            self.trajectories[track_id] = self.trajectories[track_id][-max_len:]

    def get_trajectory(self, track_id: int) -> List[Tuple[int, int]]:
        """Get position history for a single track."""
        return self.trajectories.get(track_id, [])

    def cleanup_old_tracks(self, active_ids: Set[int]):
        """
        Remove trajectories and state for tracks that have been inactive
        for longer than 2x track_buffer frames to prevent memory leaks.
        """
        threshold_frames = 2 * self.track_buffer
        expired_ids = [
            tid for tid, last_frame in self.last_seen_frame.items()
            if tid not in active_ids and (self.frame_count - last_frame) > threshold_frames
        ]

        for tid in expired_ids:
            if tid in self.trajectories:
                del self.trajectories[tid]
            if tid in self.last_seen_frame:
                del self.last_seen_frame[tid]

        # Keep seen_ids bounded to last 5000 IDs
        if len(self.seen_ids) > 5000:
            self.seen_ids = set(list(self.seen_ids)[-2500:])

    def reset(self):
        """Reset all active tracks, trajectories, and frame counts for a new session or loop."""
        self.trajectories.clear()
        self.last_seen_frame.clear()
        self.seen_ids.clear()
        self.frame_count = 0
        try:
            if hasattr(self.model, 'predictor') and self.model.predictor is not None:
                if hasattr(self.model.predictor, 'trackers'):
                    self.model.predictor.trackers = []
        except Exception:
            pass
