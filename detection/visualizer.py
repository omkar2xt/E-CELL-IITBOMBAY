# visualizer.py
# ============================================================
# Everything related to "drawing things on the frame" is here.
# Separated from logic so if we want to change the appearance,
# we don't need to touch the detector or main.
# ============================================================

import cv2
import numpy as np
import time
from typing import List
from detector import Detection
import config


class Visualizer:
    """
    Draws bounding boxes, labels, and info panels on the frame.
    """

    def __init__(self):
        # For FPS calculation
        self._prev_time = time.time()
        self._fps = 0.0
        self._fps_smoothed = 0.0     # Smoothed FPS to avoid jitter

    def draw(self, frame: np.ndarray, detections: List[Detection]) -> np.ndarray:
        """
        Main entry point. Draws all overlays onto the frame.

        Args:
            frame: original frame from camera/video
            detections: list of Detections from PersonDetector

        Returns:
            frame with overlays added (in-place edit)
        """
        # Calculate FPS first
        self._update_fps()

        # 1. Draw bounding box for each person
        for det in detections:
            self._draw_person_box(frame, det)

        # 2. Draw info panel in the top-left corner
        self._draw_info_panel(frame, len(detections))

        return frame

    def _draw_person_box(self, frame: np.ndarray, det: Detection):
        """
        Draw a single bounding box + confidence label.

        Box color slightly changes depending on confidence:
        - High confidence (>0.7) -> brighter/solid
        - Low confidence (0.4-0.7) -> slightly faded
        This helps identify "hesitant" detections.
        """
        x1, y1, x2, y2 = [int(v) for v in det.bbox]

        # Adjust color opacity based on confidence
        alpha = 0.5 + (det.confidence * 0.5)   # range: 0.7 - 1.0
        b, g, r = config.BOX_COLOR
        color = (int(b * alpha), int(g * alpha), int(r * alpha))

        # Draw bounding box rectangle
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, config.BOX_THICKNESS)

        # Confidence label above the box
        if config.DISPLAY_CONFIDENCE:
            label = f"{det.confidence:.0%}"  # e.g.: "87%"
            self._draw_label(frame, label, x1, y1, color)

        # Center point - useful for tracking debugging (week 2)
        cx, cy = det.center
        cv2.circle(frame, (cx, cy), 3, color, -1)

    def _draw_label(self, frame, text, x, y, color):
        """
        Draw text with a dark background to make it readable
        on any background (bright or dark).
        """
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = config.FONT_SCALE
        thickness = 1

        # Text size to determine background size
        (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)

        # Background rectangle
        pad = 3
        cv2.rectangle(
            frame,
            (x, y - th - pad * 2),
            (x + tw + pad * 2, y),
            config.INFO_BG_COLOR,
            -1  # -1 = filled
        )

        # Text over the background
        cv2.putText(
            frame, text,
            (x + pad, y - pad),
            font, scale, config.TEXT_COLOR, thickness,
            cv2.LINE_AA
        )

    def _draw_info_panel(self, frame, person_count: int):
        """
        Info panel in the top-left corner:
        - Number of detected people
        - FPS
        - Active confidence threshold
        """
        h, w = frame.shape[:2]

        # Semi-transparent panel background
        panel_h = 90
        panel_w = 240
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (panel_w, panel_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        font = cv2.FONT_HERSHEY_SIMPLEX
        lines = []

        if config.DISPLAY_COUNT:
            lines.append(f"Persons detected: {person_count}")

        if config.DISPLAY_FPS:
            lines.append(f"FPS: {self._fps_smoothed:.1f}")

        lines.append(f"Conf threshold: {config.CONFIDENCE_THRESHOLD:.0%}")

        for i, line in enumerate(lines):
            y = 22 + i * 24
            cv2.putText(
                frame, line,
                (10, y),
                font, 0.55, config.TEXT_COLOR, 1,
                cv2.LINE_AA
            )

        # Thin separator line below the panel
        cv2.line(frame, (0, panel_h), (panel_w, panel_h), (80, 80, 80), 1)

    def _update_fps(self):
        """Calculate FPS using exponential smoothing to prevent jitter."""
        now = time.time()
        dt = now - self._prev_time
        self._prev_time = now

        if dt > 0:
            raw_fps = 1.0 / dt
            # Exponential moving average: smoother than raw FPS
            self._fps_smoothed = 0.9 * self._fps_smoothed + 0.1 * raw_fps
            self._fps = raw_fps