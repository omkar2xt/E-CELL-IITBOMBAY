# demographic.py
# ============================================================
# Estimasi usia dan gender dari wajah yang terdeteksi.
# Menggunakan DeepFace HANYA untuk attribute estimation,
# bukan face recognition. Tidak ada embedding atau identitas
# yang disimpan.
#
# Privacy design:
# - Frame wajah diproses lalu langsung dibuang dari memori
# - Hanya statistik agregat yang disimpan (distribusi usia/gender)
# - Tidak ada mapping antara Track ID dan hasil demografi
#
# Kenapa tidak run tiap frame?
# DeepFace butuh ~100-300ms per wajah. Di 30fps, kalau run tiap
# frame dengan 5 orang = 5 * 200ms = 1000ms per frame = 1fps.
# Solusi: run setiap N frame, hasil di-cache sampai update berikutnya.
# ============================================================

import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
from collections import Counter, deque
import threading
import time
import config

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tracking'))
from tracker import TrackedPerson


class DemographicEstimator:
    """
    Estimasi demografi dari bounding box orang.

    Menggunakan face crop dari bounding box orang (bukan dedicated
    face detector dulu) untuk kecepatan. DeepFace akan coba detect
    wajah dari crop tersebut.

    Run di background thread supaya tidak block main pipeline.
    """

    def __init__(self):
        self._enabled = False
        self._lock = threading.Lock()

        # History agregat (bukan per-individu)
        self._age_history: deque = deque(maxlen=config.DEMO_HISTORY_SIZE)
        self._gender_history: deque = deque(maxlen=config.DEMO_HISTORY_SIZE)

        # Cache hasil terbaru untuk display
        self._latest_results: Dict = {
            "age_distribution": {},
            "gender_distribution": {},
            "sample_count": 0,
            "last_update": None,
        }

        self._frame_counter = 0
        self._processing = False   # flag: sedang proses di background?

        # Coba import DeepFace
        self._try_init_deepface()

    def _try_init_deepface(self):
        """
        DeepFace adalah optional dependency.
        Kalau tidak terinstall, module tetap jalan tanpa demografi.
        """
        try:
            from deepface import DeepFace
            self._DeepFace = DeepFace
            self._enabled = True
            print("[Demographic] DeepFace loaded. Estimasi demografi aktif.")
            print(f"[Demographic] Backend: {config.DEMO_DETECTOR_BACKEND}")
            # BENAR
            print(f"[Demographic] Interval: setiap {config.DEMO_ANALYSIS_INTERVAL} frame")
        except ImportError:
            self._enabled = False
            print("[Demographic] DeepFace tidak terinstall. Demografi dinonaktifkan.")
            print("             Install dengan: pip install deepface tf-keras")

    def update(self, frame: np.ndarray, tracked_persons: List[TrackedPerson]):
        """
        Panggil setiap frame. Akan run analisis setiap DEMO_INTERVAL frame.
        Analisis berjalan di background thread.
        """
        if not self._enabled:
            return

        self._frame_counter += 1

        # Hanya proses setiap N frame dan kalau tidak sedang processing
        if self._frame_counter % config.DEMO_ANALYSIS_INTERVAL != 0:
            return
        if self._processing:
            return
        if not tracked_persons:
            return

        # Crop wajah dari bounding box orang
        # Ambil bagian atas bbox (area kepala/wajah ~30% dari tinggi)
        crops = []
        for person in tracked_persons:
            crop = self._extract_face_region(frame, person)
            if crop is not None:
                crops.append(crop)

        if not crops:
            return

        # Jalankan DeepFace di background thread
        self._processing = True
        thread = threading.Thread(
            target=self._analyze_crops,
            args=(crops,),
            daemon=True
        )
        thread.start()

    def _extract_face_region(
        self,
        frame: np.ndarray,
        person: TrackedPerson
    ) -> Optional[np.ndarray]:
        """
        Crop area kepala dari bounding box orang.

        Strategi: ambil 35% teratas dari bounding box.
        Ini bukan deteksi wajah yang presisi, tapi cukup untuk
        memberi DeepFace area yang mengandung wajah.
        DeepFace akan re-detect wajah di dalam crop ini.
        """
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = [int(v) for v in person.bbox]

        box_h = y2 - y1
        face_y2 = y1 + int(box_h * 0.40)   # 40% teratas

        # Pastikan dalam batas frame
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        face_y2 = min(h, face_y2)

        if x2 - x1 < 20 or face_y2 - y1 < 20:
            return None   # terlalu kecil

        crop = frame[y1:face_y2, x1:x2].copy()
        return crop

    def _analyze_crops(self, crops: List[np.ndarray]):
        """
        Jalankan DeepFace pada list crop. Background thread.
        Hanya simpan statistik agregat, bukan data per-individu.
        """
        try:
            ages = []
            genders = []

            for crop in crops:
                try:
                    result = self._DeepFace.analyze(
                        crop,
                        actions=["age", "gender"],   # TIDAK include "identity"
                        detector_backend=config.DEMO_DETECTOR_BACKEND,
                        enforce_detection=False,      # tidak error kalau wajah tidak ketemu
                        silent=True
                    )

                    # result bisa list (multiple faces) atau dict (single face)
                    if isinstance(result, list):
                        result = result[0]

                    age = result.get("age")
                    gender_dict = result.get("gender", {})

                    if age is not None:
                        # Bin ke kelompok usia
                        age_group = self._age_to_group(int(age))
                        ages.append(age_group)

                    if gender_dict:
                        # Ambil gender dengan confidence tertinggi
                        dominant = max(gender_dict, key=gender_dict.get)
                        genders.append(dominant)

                except Exception:
                    # Wajah tidak terdeteksi di crop ini, skip
                    continue

            # Update history agregat (thread-safe)
            with self._lock:
                self._age_history.extend(ages)
                self._gender_history.extend(genders)
                self._update_latest_results()

        finally:
            self._processing = False

    def _age_to_group(self, age: int) -> str:
        """Konversi usia ke kelompok untuk privasi dan readability."""
        if age < 18:   return "< 18"
        elif age < 25: return "18-24"
        elif age < 35: return "25-34"
        elif age < 45: return "35-44"
        elif age < 55: return "45-54"
        elif age < 65: return "55-64"
        else:          return "65+"

    def _update_latest_results(self):
        """Hitung distribusi dari history. Panggil dengan lock."""
        age_counts = Counter(self._age_history)
        gender_counts = Counter(self._gender_history)

        total_age = sum(age_counts.values()) or 1
        total_gen = sum(gender_counts.values()) or 1

        self._latest_results = {
            "age_distribution": {
                k: round(v / total_age * 100, 1)
                for k, v in sorted(age_counts.items())
            },
            "gender_distribution": {
                k: round(v / total_gen * 100, 1)
                for k, v in gender_counts.items()
            },
            "sample_count": len(self._age_history),
            "last_update": time.strftime("%H:%M:%S"),
        }

    def get_results(self) -> Dict:
        """Ambil hasil terbaru. Thread-safe."""
        with self._lock:
            return dict(self._latest_results)

    @property
    def is_enabled(self) -> bool:
        return self._enabled