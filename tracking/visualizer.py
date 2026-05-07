# visualizer.py
# ============================================================
# Extends the visualizer from detection/ with additions:
# - Track ID label above the bounding box
# - Trajectory (movement trail)
# - Virtual line with counter
# - Crossing event flash
# ============================================================

import cv2
import numpy as np
import time
from typing import List, Tuple
from tracker import TrackedPerson
from counter import LineCounter
import config as config


class TrackingVisualizer:

    def __init__(self):
        self._prev_time = time.time()
        self._fps_smoothed = 0.0

        # Flash effect on crossing: (frame_countdown, direction)
        self._flash_frames = 0
        self._flash_direction = ""

    def draw(
        self,
        frame: np.ndarray,
        tracked_persons: List[TrackedPerson],
        counter: LineCounter,
        tracker_trajectories: dict
    ) -> np.ndarray:
        """
        Draw all overlays onto the frame.

        Args:
            frame: BGR frame from OpenCV
            tracked_persons: list from PersonTracker.update()
            counter: LineCounter instance (to fetch counts)
            tracker_trajectories: dict {track_id: [(cx,cy), ...]}
        """
        self._update_fps()

        # Update flash state if there's a crossing
        if counter.has_crossing_this_frame():
            self._flash_frames = 8  # flash for 8 frames
            self._flash_direction = counter.current_crossings[-1][1]

        # 1. Draw trajectories first (bottom layer)
        for person in tracked_persons:
            traj = tracker_trajectories.get(person.track_id, [])
            self._draw_trajectory(frame, traj)

        # 2. Draw virtual counting line
        self._draw_counting_line(frame, counter)

        # 3. Draw bounding boxes + track IDs
        for person in tracked_persons:
            self._draw_tracked_person(frame, person)

        # 4. Info panel
        self._draw_info_panel(frame, tracked_persons, counter)

        # 5. Crossing flash effect
        if self._flash_frames > 0:
            self._draw_crossing_flash(frame)
            self._flash_frames -= 1

        return frame

    def _draw_tracked_person(self, frame: np.ndarray, person: TrackedPerson):
        """Bounding box + Track ID label."""
        x1, y1, x2, y2 = [int(v) for v in person.bbox]

        # Box color based on confidence
        alpha = 0.6 + person.confidence * 0.4
        b, g, r = config.BOX_COLOR
        box_color = (int(b * alpha), int(g * alpha), int(r * alpha))

        # Bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, config.BOX_THICKNESS)

        # Label: "ID:5  87%"
        label = f"ID:{person.track_id}"
        if config.DISPLAY_CONFIDENCE:
            label += f"  {person.confidence:.0%}"

        self._draw_label(frame, label, x1, y1, config.TRACK_ID_COLOR)

        # Bottom center point (counting reference)
        bcx, bcy = person.bottom_center
        cv2.circle(frame, (bcx, bcy), 4, config.TRACK_ID_COLOR, -1)

    def _draw_trajectory(self, frame: np.ndarray, trajectory: list):
        """
        Draw movement history as a polyline.
        Older segments fade out.
        """
        if len(trajectory) < 2:
            return

        n = len(trajectory)
        for i in range(1, n):
            # Fade: older points are more transparent
            fade = i / n  # 0.0 (oldest) -> 1.0 (newest)
            b, g, r = config.TRAJECTORY_COLOR
            color = (int(b * fade), int(g * fade), int(r * fade))
            thickness = 1 if fade < 0.5 else 2

            cv2.line(frame, trajectory[i-1], trajectory[i], color, thickness, cv2.LINE_AA)

    def _draw_counting_line(self, frame: np.ndarray, counter: LineCounter):
        """
        Draw the virtual counting line.
        Flashes red during a crossing event.
        """
        color = config.LINE_COLOR_ALERT if self._flash_frames > 0 else config.LINE_COLOR
        thickness = 3 if self._flash_frames > 0 else 2

        cv2.line(
            frame,
            counter.line_start,
            counter.line_end,
            color,
            thickness,
            cv2.LINE_AA
        )

        # Label at the start of the line
        lx, ly = counter.line_start
        cv2.putText(
            frame, "COUNT LINE",
            (lx + 5, ly + 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45,
            color, 1, cv2.LINE_AA
        )

    def _draw_info_panel(
        self,
        frame: np.ndarray,
        tracked_persons: List[TrackedPerson],
        counter: LineCounter
    ):
        """
        Top-left info panel:
        - People currently in frame
        - Total IN / OUT
        - Occupancy (estimated number of people inside)
        - FPS
        """
        panel_w, panel_h = 250, 115
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (panel_w, panel_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

        font = cv2.FONT_HERSHEY_SIMPLEX
        lines = [
            f"In frame  : {len(tracked_persons)}",
            f"Total IN  : {counter.count_in}",
            f"Total OUT : {counter.count_out}",
            f"Occupancy : {counter.current_occupancy}",
            f"FPS       : {self._fps_smoothed:.1f}",
        ]

        for i, line in enumerate(lines):
            y = 20 + i * 20
            cv2.putText(frame, line, (10, y), font, 0.52, config.TEXT_COLOR, 1, cv2.LINE_AA)

        cv2.line(frame, (0, panel_h), (panel_w, panel_h), (80, 80, 80), 1)

    def _draw_crossing_flash(self, frame: np.ndarray):
        """
        Color overlay on the edge of the frame during crossing.
        Green = IN, Red = OUT.
        """
        h, w = frame.shape[:2]
        color = (0, 200, 50) if self._flash_direction == "IN" else (0, 50, 220)
        intensity = int(60 * (self._flash_frames / 8))

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), color, 20)
        cv2.addWeighted(overlay, intensity / 255, frame, 1 - intensity / 255, 0, frame)

        # Crossing text at bottom center
        text = f"  {self._flash_direction}  "
        tw, th = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)[0]
        tx = (w - tw) // 2
        ty = h - 30
        cv2.putText(frame, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 2, cv2.LINE_AA)

    def _draw_label(self, frame, text, x, y, color):
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = config.FONT_SCALE
        (tw, th), _ = cv2.getTextSize(text, font, scale, 1)
        pad = 3
        cv2.rectangle(frame, (x, y - th - pad*2), (x + tw + pad*2, y), (0, 0, 0), -1)
        cv2.putText(frame, text, (x + pad, y - pad), font, scale, color, 1, cv2.LINE_AA)

    def _update_fps(self):
        now = time.time()
        dt = now - self._prev_time
        self._prev_time = now
        if dt > 0:
            self._fps_smoothed = 0.9 * self._fps_smoothed + 0.1 * (1.0 / dt)