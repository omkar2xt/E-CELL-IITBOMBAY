# visualizer.py
# ============================================================
# Semua urusan "gambar sesuatu di atas frame" ada di sini.
# Dipisah dari logic supaya kalau mau ganti tampilan,
# tidak perlu sentuh detector atau main.
# ============================================================

import cv2
import numpy as np
import time
from typing import List
from detector import Detection
import config


class Visualizer:
    """
    Menggambar bounding box, label, dan info panel di atas frame.
    """

    def __init__(self):
        # Untuk kalkulasi FPS
        self._prev_time = time.time()
        self._fps = 0.0
        self._fps_smoothed = 0.0     # FPS yang di-smooth supaya tidak jitter

    def draw(self, frame: np.ndarray, detections: List[Detection]) -> np.ndarray:
        """
        Entry point utama. Gambar semua overlay ke frame.

        Args:
            frame: frame original dari kamera/video
            detections: list Detection dari PersonDetector

        Returns:
            frame yang sudah ada overlay-nya (in-place edit)
        """
        # Hitung FPS dulu
        self._update_fps()

        # 1. Gambar bounding box untuk tiap orang
        for det in detections:
            self._draw_person_box(frame, det)

        # 2. Gambar info panel di pojok kiri atas
        self._draw_info_panel(frame, len(detections))

        return frame

    def _draw_person_box(self, frame: np.ndarray, det: Detection):
        """
        Gambar satu bounding box + label confidence.

        Warna box sedikit berubah tergantung confidence:
        - Confidence tinggi (>0.7) → lebih terang/solid
        - Confidence rendah (0.4-0.7) → sedikit lebih pudar
        Ini membantu identifikasi deteksi yang "ragu-ragu".
        """
        x1, y1, x2, y2 = [int(v) for v in det.bbox]

        # Sesuaikan opacity warna berdasarkan confidence
        alpha = 0.5 + (det.confidence * 0.5)   # range: 0.7 - 1.0
        b, g, r = config.BOX_COLOR
        color = (int(b * alpha), int(g * alpha), int(r * alpha))

        # Gambar rectangle bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, config.BOX_THICKNESS)

        # Label confidence di atas box
        if config.DISPLAY_CONFIDENCE:
            label = f"{det.confidence:.0%}"  # misal: "87%"
            self._draw_label(frame, label, x1, y1, color)

        # Titik tengah — berguna untuk debug tracking (minggu 2)
        cx, cy = det.center
        cv2.circle(frame, (cx, cy), 3, color, -1)

    def _draw_label(self, frame, text, x, y, color):
        """
        Gambar teks dengan background gelap supaya mudah dibaca
        di background apapun (terang maupun gelap).
        """
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = config.FONT_SCALE
        thickness = 1

        # Ukuran teks untuk menentukan ukuran background
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

        # Teks di atas background
        cv2.putText(
            frame, text,
            (x + pad, y - pad),
            font, scale, config.TEXT_COLOR, thickness,
            cv2.LINE_AA
        )

    def _draw_info_panel(self, frame, person_count: int):
        """
        Panel info di pojok kiri atas:
        - Jumlah orang yang terdeteksi
        - FPS
        - Confidence threshold yang aktif
        """
        h, w = frame.shape[:2]

        # Background panel semi-transparan
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

        # Garis separator tipis di bawah panel
        cv2.line(frame, (0, panel_h), (panel_w, panel_h), (80, 80, 80), 1)

    def _update_fps(self):
        """Hitung FPS dengan exponential smoothing supaya tidak jitter."""
        now = time.time()
        dt = now - self._prev_time
        self._prev_time = now

        if dt > 0:
            raw_fps = 1.0 / dt
            # Exponential moving average: lebih smooth daripada raw FPS
            self._fps_smoothed = 0.9 * self._fps_smoothed + 0.1 * raw_fps
            self._fps = raw_fps