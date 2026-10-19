# detector.py
# ============================================================
# Person detection wrapper around YOLO11 for StorePulse AI.
# Provides structured bounding box and confidence estimations.
# ============================================================

import sys
import os
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np

try:
    from detection import config
except ImportError:
    import config

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """
    Structured representation of a single person detection in a video frame.
    Supports downstream tracking, demographic analysis, and dwell mapping.
    """
    bbox: List[float]       # [x1, y1, x2, y2] - bounding box coordinates
    confidence: float       # 0.0 - 1.0, confidence score for person class
    class_id: int = 0       # Class index (0 for person)

    @property
    def center(self) -> Tuple[int, int]:
        """Center coordinates (x, y) of the bounding box for spatial tracking."""
        x1, y1, x2, y2 = self.bbox
        return (int((x1 + x2) / 2), int((y1 + y2) / 2))

    @property
    def bottom_center(self) -> Tuple[int, int]:
        """
        Bottom center point of the bounding box.
        Represents ground-plane foot position for accurate zone containment.
        """
        x1, y1, x2, y2 = self.bbox
        return (int((x1 + x2) / 2), int(y2))

    @property
    def width(self) -> float:
        return max(0.0, float(self.bbox[2] - self.bbox[0]))

    @property
    def height(self) -> float:
        return max(0.0, float(self.bbox[3] - self.bbox[1]))

    @property
    def area(self) -> float:
        return self.width * self.height


class PersonDetector:
    """
    Wrapper for YOLO11 specifically to detect people.
    Encapsulates model initialization, inference error handling, and structured outputs.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
        device: Optional[str] = None,
    ):
        self.model_name = model_name or getattr(config, 'MODEL_NAME', 'yolo11n.pt')
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else getattr(config, 'CONFIDENCE_THRESHOLD', 0.4)
        )
        self.device = device
        self.is_loaded = False
        self.model = None

        self._load_model()

    def _load_model(self):
        try:
            from ultralytics import YOLO
            print(f"[Detector] Loading model: {self.model_name}")
            self.model = YOLO(self.model_name)
            self.is_loaded = True
            print(f"[Detector] Model loaded successfully! Confidence threshold: {self.confidence_threshold}")
        except Exception as e:
            logger.error(f"[Detector] Failed to load model {self.model_name}: {e}")
            print(f"[Detector] Error: Model loading failed: {e}")
            self.model = None
            self.is_loaded = False

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Process one frame and return a list of Detections.

        Args:
            frame: numpy BGR array from OpenCV (shape: H x W x 3)

        Returns:
            List[Detection]: all people detected in this frame
        """
        if not self.is_loaded or self.model is None:
            logger.warning("[Detector] Inference called but model is not loaded.")
            return []

        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0 or len(frame.shape) < 3:
            return []

        h, w = frame.shape[:2]
        if h <= 0 or w <= 0:
            return []

        try:
            # Run YOLO inference
            # classes=[0]: COCO person class
            results = self.model(
                frame,
                classes=[getattr(config, 'CLASS_PERSON', 0)],
                conf=self.confidence_threshold,
                verbose=False,
                device=self.device
            )
        except Exception as e:
            logger.error(f"[Detector] Inference execution error: {e}")
            return []

        detections = []
        if not results or len(results) == 0:
            return detections

        first_res = results[0]
        if first_res.boxes is None or len(first_res.boxes) == 0:
            return detections

        for box in first_res.boxes:
            try:
                raw_bbox = box.xyxy[0].cpu().numpy().tolist()
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())

                # Validate coordinates within frame boundaries
                x1 = max(0.0, min(float(w), float(raw_bbox[0])))
                y1 = max(0.0, min(float(h), float(raw_bbox[1])))
                x2 = max(x1, min(float(w), float(raw_bbox[2])))
                y2 = max(y1, min(float(h), float(raw_bbox[3])))

                detections.append(Detection(
                    bbox=[x1, y1, x2, y2],
                    confidence=conf,
                    class_id=cls_id
                ))
            except Exception as e:
                logger.debug(f"[Detector] Error parsing box: {e}")
                continue

        return detections

    def get_person_count(self, detections: List[Detection]) -> int:
        """Number of people detected in this frame."""
        return len(detections)