# visualizer.py - analytics module
# ============================================================
# Extend tracking visualizer dengan:
# - Trajectory overlay
# - Counting line + crossing flash
# - Demographic label per person
# - Info panel kiri atas (count, IN/OUT, FPS)
# - Demographic panel kanan atas (gender + age distribution)
# ============================================================

import cv2
import numpy as np
import time
from typing import List
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tracking'))
from tracker import TrackedPerson
from counter import LineCounter

import config


class AnalyticsVisualizer:

    def __init__(self):
        self._prev_time = time.time()
        self._fps_smoothed = 0.0
        self._flash_frames = 0
        self._flash_direction = ""

    def draw(
        self,
        frame: np.ndarray,
        tracked_persons: List[TrackedPerson],
        counter: LineCounter,
        trajectories: dict,
        queue,           # QueueMonitor instance
        demo,            # DemographicEstimator instance
    ) -> np.ndarray:
        """
        Gambar semua overlay analytics ke frame.
        Heatmap dan queue zone sudah di-apply sebelum masuk sini (di main.py).
        """
        self._update_fps()

        # Update crossing flash state
        if counter.has_crossing_this_frame():
            self._flash_frames = 8
            self._flash_direction = counter.current_crossings[-1][1]

        # 1. Trajectory (layer paling bawah dari overlay ini)
        for person in tracked_persons:
            traj = trajectories.get(person.track_id, [])
            self._draw_trajectory(frame, traj)

        # 2. Counting line
        self._draw_counting_line(frame, counter)

        # 3. Bounding box + Track ID + label demografi
        for person in tracked_persons:
            self._draw_tracked_person(frame, person, demo)

        # 4. Info panel kiri atas
        self._draw_info_panel(frame, tracked_persons, counter, queue)

        # 5. Demographic panel kanan atas
        if demo.is_enabled and demo.get_results().get("sample_count", 0) > 0:
            self._draw_demo_panel(frame, demo)

        # 6. Crossing flash
        if self._flash_frames > 0:
            self._draw_crossing_flash(frame)
            self._flash_frames -= 1

        return frame

    # ── Drawing helpers ──

    def _draw_tracked_person(self, frame, person: TrackedPerson, demo):
        x1, y1, x2, y2 = [int(v) for v in person.bbox]

        alpha = 0.6 + person.confidence * 0.4
        b, g, r = config.BOX_COLOR
        color = (int(b * alpha), int(g * alpha), int(r * alpha))
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, config.BOX_THICKNESS)

        label = f"ID:{person.track_id}  {person.confidence:.0%}"
        self._draw_label(frame, label, x1, y1, config.TRACK_ID_COLOR)

        # ← hapus bagian demo.get_result per track_id, tidak ada di class
        # demografi tidak di-map ke individu by design (privacy)

        cv2.circle(frame, person.bottom_center, 4, config.TRACK_ID_COLOR, -1)

    def _draw_trajectory(self, frame, trajectory):
        if len(trajectory) < 2:
            return
        n = len(trajectory)
        for i in range(1, n):
            fade = i / n
            b, g, r = config.TRAJECTORY_COLOR
            color = (int(b * fade), int(g * fade), int(r * fade))
            cv2.line(frame, trajectory[i-1], trajectory[i],
                     color, 1 if fade < 0.5 else 2, cv2.LINE_AA)

    def _draw_counting_line(self, frame, counter: LineCounter):
        color = config.LINE_COLOR_ALERT if self._flash_frames > 0 else config.LINE_COLOR
        thickness = 3 if self._flash_frames > 0 else 2
        cv2.line(frame, counter.line_start, counter.line_end, color, thickness, cv2.LINE_AA)
        lx, ly = counter.line_start
        cv2.putText(frame, "COUNT LINE", (lx + 5, ly + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    def _draw_info_panel(self, frame, tracked_persons, counter, queue):
        """Panel kiri atas: tracking stats + queue count + FPS."""
        panel_w, panel_h = 255, 135
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (panel_w, panel_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

        queue_str = str(queue.current_count)
        if queue.is_alert:
            queue_str += " (!)"

        lines = [
            f"In frame  : {len(tracked_persons)}",
            f"Total IN  : {counter.count_in}",
            f"Total OUT : {counter.count_out}",
            f"Occupancy : {counter.current_occupancy}",
            f"Queue     : {queue_str}",
            f"FPS       : {self._fps_smoothed:.1f}",
        ]
        for i, line in enumerate(lines):
            color = config.QUEUE_ZONE_COLOR_ALERT if (i == 4 and queue.is_alert) else config.TEXT_COLOR
            cv2.putText(frame, line, (10, 20 + i * 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 1, cv2.LINE_AA)

        cv2.line(frame, (0, panel_h), (panel_w, panel_h), (80, 80, 80), 1)

    def _draw_demo_panel(self, frame, demo):
        fh, fw = frame.shape[:2]
        panel_w, panel_h = 210, 145
        px = fw - panel_w - 5

        # Ambil data via get_results()
        results = demo.get_results()
        n = results.get("sample_count", 0)
        if n == 0:
            return

        overlay = frame.copy()
        cv2.rectangle(overlay, (px, 0), (fw - 5, panel_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, f"Demographics  (n={n})",
                    (px + 5, 15), font, 0.42, (200, 200, 200), 1, cv2.LINE_AA)

        y = 32
        gender = results.get("gender_distribution", {})
        total_g = sum(gender.values()) or 1
        for g_label, pct in gender.items():
            bar_color = (200, 120, 50) if "woman" in g_label.lower() else (50, 150, 220)
            bar_w = int((pct / 100) * (panel_w - 85))
            cv2.rectangle(frame, (px + 75, y - 11), (px + 75 + bar_w, y + 1), bar_color, -1)
            cv2.putText(frame, f"{g_label[:3]}  {pct:.0f}%",
                        (px + 5, y), font, 0.42, config.TEXT_COLOR, 1, cv2.LINE_AA)
            y += 20

        y += 4
        cv2.line(frame, (px, y), (fw - 5, y), (60, 60, 60), 1)
        y += 12

        age = results.get("age_distribution", {})
        total_a = sum(age.values()) or 1
        sorted_age = sorted(age.items(), key=lambda x: x[1], reverse=True)[:4]
        for age_label, pct in sorted_age:
            bar_w = int((pct / 100) * (panel_w - 85))
            cv2.rectangle(frame, (px + 75, y - 11), (px + 75 + bar_w, y + 1), (80, 200, 120), -1)
            cv2.putText(frame, f"{age_label}  {pct:.0f}%",
                        (px + 5, y), font, 0.40, config.TEXT_COLOR, 1, cv2.LINE_AA)
            y += 18

        cv2.line(frame, (px, panel_h), (fw - 5, panel_h), (80, 80, 80), 1)

    def _draw_crossing_flash(self, frame):
        h, w = frame.shape[:2]
        color = (0, 200, 50) if self._flash_direction == "IN" else (0, 50, 220)
        intensity = int(60 * (self._flash_frames / 8))
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), color, 20)
        cv2.addWeighted(overlay, intensity / 255, frame, 1 - intensity / 255, 0, frame)
        text = f"  {self._flash_direction}  "
        tw = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)[0][0]
        cv2.putText(frame, text, ((w - tw) // 2, h - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 2, cv2.LINE_AA)

    def _draw_label(self, frame, text, x, y, color):
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), _ = cv2.getTextSize(text, font, config.FONT_SCALE, 1)
        pad = 3
        cv2.rectangle(frame, (x, y - th - pad*2), (x + tw + pad*2, y), (0, 0, 0), -1)
        cv2.putText(frame, text, (x + pad, y - pad), font, config.FONT_SCALE, color, 1, cv2.LINE_AA)

    def _update_fps(self):
        now = time.time()
        dt = now - self._prev_time
        self._prev_time = now
        if dt > 0:
            self._fps_smoothed = 0.9 * self._fps_smoothed + 0.1 * (1.0 / dt)