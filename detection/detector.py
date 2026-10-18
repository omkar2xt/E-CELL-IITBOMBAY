# detector.py
# ============================================================
# Person detection wrapper around YOLO11 for StorePulse AI.
# Provides structured bounding box and confidence estimations.
# ============================================================

from ultralytics import YOLO
import numpy as np
from dataclasses import dataclass, field
from typing import List
import config


@dataclass
class Detection:
    """
    Structured representation of a single person detection in a video frame.
    Supports downstream tracking, demographic analysis, and dwell mapping.
    """
    bbox: List[float]       # [x1, y1, x2, y2] - bounding box coordinates
    confidence: float       # 0.0 - 1.0, confidence score for person class
    class_id: int           # Class index (0 for person)

    @property
    def center(self):
        """Center coordinates (x, y) of the bounding box for spatial tracking."""
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
    Wrapper for YOLO11 specifically to detect people.

    Why wrap it in a separate class?
    - So main.py doesn't need to know YOLO implementation details
    - If we change the model later (e.g. to YOLO12), just edit this file
    - Easy to test independently
    """

    def __init__(self):
        print(f"[Detector] Loading model: {config.MODEL_NAME}")
        print(f"[Detector] Model will auto-download if missing (~6MB for nano)")

        # Load model - first time will automatically download from Ultralytics
        self.model = YOLO(config.MODEL_NAME)
        self.confidence_threshold = config.CONFIDENCE_THRESHOLD

        print(f"[Detector] Model loaded! Confidence threshold: {self.confidence_threshold}")

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Process one frame and return a list of Detections.

        Args:
            frame: numpy BGR array from OpenCV (shape: H x W x 3)

        Returns:
            List[Detection]: all people detected in this frame
        """
        # Run YOLO
        # - classes=[0]: only detect "person" class, ignore cars, bags, etc.
        # - verbose=False: mute YOLO logs so the terminal isn't noisy
        results = self.model(
            frame,
            classes=[config.CLASS_PERSON],
            conf=self.confidence_threshold,
            verbose=False
        )

        detections = []

        # results[0] because we process 1 frame per call
        # .boxes contains all detected bounding boxes
        for box in results[0].boxes:
            # .xyxy = format [x1, y1, x2, y2] in pixels
            # .cpu().numpy() = move from GPU to CPU, convert to numpy
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
        """Number of people in this frame. Simple but useful for display."""
        return len(detections)