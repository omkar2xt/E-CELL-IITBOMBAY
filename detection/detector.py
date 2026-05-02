# detector.py
# ============================================================
# Class ini membungkus YOLO11 supaya mudah dipakai.
# Minggu-minggu berikutnya kita tidak perlu ubah file ini —
# cukup import dan pakai.
# ============================================================

from ultralytics import YOLO
import numpy as np
from dataclasses import dataclass, field
from typing import List
import config


@dataclass
class Detection:
    """
    Satu detection = satu orang yang terdeteksi di frame.

    Kenapa pakai dataclass?
    Supaya data terstruktur dan mudah di-extend minggu depan
    (misalnya nanti ditambah track_id, age, gender, dll).
    """
    bbox: List[float]       # [x1, y1, x2, y2] — koordinat bounding box
    confidence: float       # 0.0 - 1.0, seberapa yakin model ini "orang"
    class_id: int           # Selalu 0 (person), tapi disimpan untuk konsistensi

    @property
    def center(self):
        """Titik tengah bounding box. Dipakai nanti untuk heatmap (minggu 3)."""
        x1, y1, x2, y2 = self.bbox
        return (int((x1 + x2) / 2), int((y1 + y2) / 2))

    @property
    def width(self):
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self):
        return self.bbox[3] - self.bbox[1]

    @property
    def area(self):
        return self.width * self.height


class PersonDetector:
    """
    Wrapper untuk YOLO11 yang khusus detect orang.

    Kenapa dibungkus ke class terpisah?
    - Supaya main.py tidak tahu detail implementasi YOLO
    - Kalau nanti ganti model (misal ke YOLO12), cukup edit file ini
    - Mudah di-test secara terpisah
    """

    def __init__(self):
        print(f"[Detector] Loading model: {config.MODEL_NAME}")
        print(f"[Detector] Model akan auto-download jika belum ada (~6MB untuk nano)")

        # Load model — pertama kali akan download otomatis dari Ultralytics
        self.model = YOLO(config.MODEL_NAME)
        self.confidence_threshold = config.CONFIDENCE_THRESHOLD

        print(f"[Detector] Model loaded! Confidence threshold: {self.confidence_threshold}")

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Proses satu frame dan kembalikan list Detection.

        Args:
            frame: numpy array BGR dari OpenCV (shape: H x W x 3)

        Returns:
            List[Detection]: semua orang yang terdeteksi di frame ini
        """
        # Jalankan YOLO
        # - classes=[0]: hanya detect class "person", ignore mobil, tas, dll
        # - verbose=False: matikan log YOLO supaya terminal tidak berisik
        results = self.model(
            frame,
            classes=[config.CLASS_PERSON],
            conf=self.confidence_threshold,
            verbose=False
        )

        detections = []

        # results[0] karena kita proses 1 frame per call
        # .boxes berisi semua bounding box yang terdeteksi
        for box in results[0].boxes:
            # .xyxy = format [x1, y1, x2, y2] dalam pixels
            # .cpu().numpy() = pindah dari GPU ke CPU, convert ke numpy
            bbox = box.xyxy[0].cpu().numpy().tolist()
            confidence = float(box.conf[0].cpu().numpy())
            class_id = int(box.cls[0].cpu().numpy())

            detections.append(Detection(
                bbox=bbox,
                confidence=confidence,
                class_id=class_id
            ))

        return detections

    def get_person_count(self, detections: List[Detection]) -> int:
        """Jumlah orang di frame ini. Simpel tapi berguna untuk display."""
        return len(detections)