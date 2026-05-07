# queue_monitor.py
# ============================================================
# Monitor jumlah orang di zona tertentu (kasir, pintu, dll).
#
# Cara kerja:
# 1. Definisikan zona sebagai rectangle (rasio frame)
# 2. Setiap frame, hitung berapa Track ID yang bottom_center-nya
#    berada di dalam zona
# 3. Kalau melebihi threshold -> alert
#
# Kenapa rasio dan bukan pixel?
# Supaya zona portabel antar resolusi video berbeda.
# Kalau video 640x480 atau 1920x1080, zona tetap di posisi yang sama
# secara proporsional.
# ============================================================

import cv2
import numpy as np
from typing import List, Tuple
from dataclasses import dataclass, field
from collections import deque
import time
import config


@dataclass
class QueueState:
    """Snapshot state antrian di satu titik waktu."""
    count: int
    timestamp: float
    is_alert: bool


class QueueMonitor:

    def __init__(self, frame_width: int, frame_height: int):
        self.frame_width  = frame_width
        self.frame_height = frame_height

        # Konversi zona rasio ke pixel
        self.zone_px = self._ratio_to_pixel(config.QUEUE_ZONE)

        self.alert_threshold = config.QUEUE_ALERT_THRESHOLD

        # State sekarang
        self.current_count = 0
        self.is_alert = False

        # Riwayat count untuk chart (rolling window)
        self.history: deque = deque(maxlen=60)  # 60 data points terakhir

        # Track IDs yang sedang di zona
        self.ids_in_zone: set = set()

        print(f"[Queue] Zone px: {self.zone_px}, alert threshold: {self.alert_threshold}")

    def _ratio_to_pixel(self, zone_ratio: Tuple) -> Tuple[int, int, int, int]:
        """Konversi zona (rasio 0-1) ke koordinat pixel."""
        rx1, ry1, rx2, ry2 = zone_ratio
        return (
            int(rx1 * self.frame_width),
            int(ry1 * self.frame_height),
            int(rx2 * self.frame_width),
            int(ry2 * self.frame_height),
        )

    def update(self, tracked_persons) -> int:
        """
        Hitung orang di dalam zona.

        Args:
            tracked_persons: list TrackedPerson dari tracker

        Returns:
            jumlah orang di dalam zona saat ini
        """
        x1, y1, x2, y2 = self.zone_px
        self.ids_in_zone = set()

        for person in tracked_persons:
            bcx, bcy = person.bottom_center
            # Cek apakah bottom_center ada di dalam zona
            if x1 <= bcx <= x2 and y1 <= bcy <= y2:
                self.ids_in_zone.add(person.track_id)

        self.current_count = len(self.ids_in_zone)
        self.is_alert = self.current_count >= self.alert_threshold

        # Simpan ke history
        self.history.append(QueueState(
            count=self.current_count,
            timestamp=time.time(),
            is_alert=self.is_alert
        ))

        return self.current_count

    def is_in_zone(self, track_id: int) -> bool:
        return track_id in self.ids_in_zone

    def draw_zone(self, frame: np.ndarray) -> np.ndarray:
        """
        Gambar overlay zona di frame.
        Warna berubah saat alert.
        """
        x1, y1, x2, y2 = self.zone_px
        color = config.QUEUE_ZONE_COLOR_ALERT if self.is_alert else config.QUEUE_ZONE_COLOR

        # Fill semi-transparan
        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
        cv2.addWeighted(overlay, config.QUEUE_ZONE_ALPHA, frame, 1 - config.QUEUE_ZONE_ALPHA, 0, frame)

        # Border
        thickness = 3 if self.is_alert else 1
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

        # Label
        label = f"QUEUE: {self.current_count}"
        if self.is_alert:
            label += " (!)"

        cv2.putText(
            frame, label,
            (x1 + 5, y1 - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55,
            color, 2, cv2.LINE_AA
        )

        return frame

    def get_avg_count(self, last_n: int = 30) -> float:
        """Rata-rata jumlah orang di zona dalam N snapshot terakhir."""
        if not self.history:
            return 0.0
        recent = list(self.history)[-last_n:]
        return sum(s.count for s in recent) / len(recent)