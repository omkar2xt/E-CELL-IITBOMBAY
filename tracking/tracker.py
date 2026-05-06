# tracker.py
# ============================================================
# Wrapper untuk ByteTrack via Ultralytics.
#
# ByteTrack bekerja dalam 2 tahap assignment per frame:
#   1. High-confidence detections  → cocokkan ke track aktif via IoU
#   2. Low-confidence detections   → cocokkan ke track yang "hilang" sesaat
# Ini yang bikin ByteTrack lebih stabil dari DeepSORT di kerumunan.
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
    Satu orang yang sedang di-track.
    Extend dari Detection (week 1) dengan tambahan tracking info.
    """
    track_id: int               # ID unik yang konsisten antar frame
    bbox: List[float]           # [x1, y1, x2, y2]
    confidence: float

    # Riwayat posisi center untuk gambar trajectory
    # Key: track_id, Value: list of (cx, cy)
    # Disimpan di luar class supaya persist antar frame

    @property
    def center(self) -> Tuple[int, int]:
        x1, y1, x2, y2 = self.bbox
        return (int((x1 + x2) / 2), int((y1 + y2) / 2))

    @property
    def bottom_center(self) -> Tuple[int, int]:
        """
        Titik bawah tengah bounding box.
        Lebih akurat untuk crossing detection daripada center,
        karena representasi "posisi kaki" orang.
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
    Multi-person tracker menggunakan ByteTrack (via Ultralytics).

    Kenapa via Ultralytics dan bukan implement ByteTrack manual?
    - Ultralytics sudah integrate ByteTrack dengan YOLO secara optimal
    - Kalman Filter dan Hungarian assignment sudah di-tune untuk person tracking
    - Satu pipeline: detect + track dalam satu call
    """

    def __init__(self):
        print(f"[Tracker] Loading model: {config.MODEL_NAME}")
        self.model = YOLO(config.MODEL_NAME)

        # Riwayat posisi per track_id untuk gambar trajectory
        # { track_id: [(cx, cy), (cx, cy), ...] }
        self.trajectories = defaultdict(list)

        # Set track_id yang sudah pernah terlihat
        # Dipakai untuk deteksi "track baru" (orang baru masuk frame)
        self.seen_ids = set()

        print(f"[Tracker] ByteTrack ready. Buffer: {config.TRACK_BUFFER} frames")

    def update(self, frame: np.ndarray) -> List[TrackedPerson]:
        """
        Proses satu frame: detect + track semua orang.

        Returns list TrackedPerson dengan track_id yang konsisten.
        """
        # Jalankan YOLO dengan tracker ByteTrack
        # persist=True: penting! Ini yang membuat track ID konsisten
        #               antar frame. Tanpa ini, ID reset setiap frame.
        results = self.model.track(
            frame,
            classes=[config.CLASS_PERSON],
            conf=config.TRACK_THRESH,
            tracker="bytetrack.yaml",   # config ByteTrack bawaan Ultralytics
            persist=True,               # WAJIB untuk ID konsisten
            verbose=False
        )

        tracked = []

        if results[0].boxes is None or results[0].boxes.id is None:
            # Tidak ada orang terdeteksi di frame ini
            return tracked

        boxes = results[0].boxes

        for i in range(len(boxes)):
            # Ambil data per orang
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
        Simpan riwayat posisi center per track.
        Batasi panjang trajectory supaya tidak makan memori.
        """
        self.trajectories[track_id].append(center)

        # Batasi ke N frame terakhir
        max_len = config.TRAJECTORY_LENGTH   # default 30 frames
        if len(self.trajectories[track_id]) > max_len:
            self.trajectories[track_id] = self.trajectories[track_id][-max_len:]

    def get_trajectory(self, track_id: int) -> List[Tuple[int, int]]:
        """Ambil riwayat posisi untuk satu track."""
        return self.trajectories.get(track_id, [])

    def cleanup_old_tracks(self, active_ids: set):
        """
        Hapus trajectory untuk track yang sudah lama tidak aktif.
        Panggil ini setiap beberapa ratus frame untuk cegah memory leak.
        """
        dead_ids = set(self.trajectories.keys()) - active_ids
        # Hanya hapus yang sudah tidak aktif lebih dari 2x buffer
        for tid in dead_ids:
            if len(self.trajectories[tid]) > 0:
                del self.trajectories[tid]