# demographic.py
# ============================================================
# Age and gender estimation from detected faces.
#
# IMPLEMENTATION: OpenCV DNN with Caffe models (GIL Levi & Tal Hassner, 2015)
# Does not require TensorFlow - compatible with Python 3.14+.
#
# Models will be automatically downloaded to analytics/models/ on first run.
#
# Privacy design:
# - Face crops are processed and then immediately discarded from memory
# - Only aggregate statistics are saved (age/gender distribution)
# - No mapping between Track IDs and demographic results
# ============================================================

import cv2
import numpy as np
from typing import List, Dict, Optional
from collections import Counter, deque
import threading
import time
import urllib.request
import os
import config

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tracking'))
from tracker import TrackedPerson

# -- Model URLs & paths --------------------------------------
_MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')

_AGE_PROTO    = os.path.join(_MODEL_DIR, 'age_deploy.prototxt')
_AGE_MODEL    = os.path.join(_MODEL_DIR, 'age_net.caffemodel')

_GENDER_PROTO = os.path.join(_MODEL_DIR, 'gender_deploy.prototxt')
_GENDER_MODEL = os.path.join(_MODEL_DIR, 'gender_net.caffemodel')

# Small prototxt files: download from raw GitHub (reliable)
# Large caffemodel files: download from Google Drive via gdown
_DOWNLOAD_URLS = {
    _AGE_PROTO:    ('http', 'https://raw.githubusercontent.com/spmallick/learnopencv/master/AgeGender/age_deploy.prototxt'),
    _GENDER_PROTO: ('http', 'https://raw.githubusercontent.com/spmallick/learnopencv/master/AgeGender/gender_deploy.prototxt'),
    _AGE_MODEL:    ('gdrive', '1kiusFljZc9QfcIYdU2s7xrtWHTraHwmW'),
    _GENDER_MODEL: ('gdrive', '1W_moLzMlGiELyPxWiYQJ9KFaXroQ_NFQ'),
}

_AGE_BUCKETS   = ['(0-2)', '(4-6)', '(8-12)', '(15-20)', '(25-32)',
                  '(38-43)', '(48-53)', '(60-100)']
_GENDER_LABELS = ['Male', 'Female']
_MODEL_MEAN    = (78.4263377603, 87.7689143744, 114.895847746)

# OpenCV's built-in Haar Cascade - zero download required
_HAAR_CASCADE  = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'


class DemographicEstimator:
    """
    Demographic estimation using OpenCV DNN (Caffe models).
    Does not require TensorFlow - works in Python 3.14+.
    """

    def __init__(self):
        self._enabled = False
        self._lock = threading.Lock()

        self._age_history: deque    = deque(maxlen=config.DEMO_HISTORY_SIZE)
        self._gender_history: deque = deque(maxlen=config.DEMO_HISTORY_SIZE)

        self._latest_results: Dict = {
            "age_distribution": {},
            "gender_distribution": {},
            "sample_count": 0,
            "last_update": None,
        }

        self._frame_counter = 0
        self._processing    = False

        self._face_cascade = None
        self._age_net      = None
        self._gender_net   = None

        self._try_init()

    # -- Init ------------------------------------------------

    def _try_init(self):
        """Download models if missing, then load via OpenCV DNN."""
        try:
            os.makedirs(_MODEL_DIR, exist_ok=True)
            self._download_models()
            self._load_nets()
            self._enabled = True
            print("[Demographic] OpenCV DNN models loaded. Age/gender estimation active.")
        except Exception as e:
            self._enabled = False
            print(f"[Demographic] Failed to init: {e}")
            print("             Demographic panel will be hidden in dashboard.")

    def _download_models(self):
        for path, (method, source) in _DOWNLOAD_URLS.items():
            if os.path.exists(path):
                continue
            filename = os.path.basename(path)
            print(f"[Demographic] Downloading {filename}...")
            try:
                if method == 'http':
                    urllib.request.urlretrieve(source, path)
                elif method == 'gdrive':
                    import gdown
                    gdown.download(id=source, output=path, quiet=False)
                print(f"[Demographic]   OK: {filename}")
            except Exception as e:
                raise RuntimeError(f"Failed to download {filename}: {e}")

    def _load_nets(self):
        # Haar Cascade for face detection (built into OpenCV, zero download)
        self._face_cascade = cv2.CascadeClassifier(_HAAR_CASCADE)
        # Caffe models for age/gender
        self._age_net    = cv2.dnn.readNetFromCaffe(_AGE_PROTO, _AGE_MODEL)
        self._gender_net = cv2.dnn.readNetFromCaffe(_GENDER_PROTO, _GENDER_MODEL)

    # -- Main update loop ------------------------------------

    def update(self, frame: np.ndarray, tracked_persons: List[TrackedPerson]):
        if not self._enabled:
            return

        self._frame_counter += 1
        if self._frame_counter % config.DEMO_ANALYSIS_INTERVAL != 0:
            return
        if self._processing:
            return
        if not tracked_persons:
            return

        crops = []
        for person in tracked_persons:
            crop = self._extract_face_region(frame, person)
            if crop is not None:
                crops.append(crop)

        if not crops:
            return

        self._processing = True
        thread = threading.Thread(
            target=self._analyze_crops,
            args=(crops,),
            daemon=True
        )
        thread.start()

    # -- Internal helpers ------------------------------------

    def _extract_face_region(
        self,
        frame: np.ndarray,
        person: TrackedPerson
    ) -> Optional[np.ndarray]:
        """Crop the head area (top 40% of bbox) for analysis."""
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = [int(v) for v in person.bbox]

        box_h   = y2 - y1
        face_y2 = y1 + int(box_h * 0.40)

        x1      = max(0, x1)
        y1      = max(0, y1)
        x2      = min(w, x2)
        face_y2 = min(h, face_y2)

        if x2 - x1 < 30 or face_y2 - y1 < 30:
            return None

        return frame[y1:face_y2, x1:x2].copy()

    def _analyze_crops(self, crops: List[np.ndarray]):
        """
        Run face detection + age/gender inference on a list of crops.
        Runs in a background thread - only saves aggregate statistics.
        """
        try:
            ages    = []
            genders = []

            for crop in crops:
                try:
                    gray  = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                    faces = self._face_cascade.detectMultiScale(
                        gray, scaleFactor=1.1, minNeighbors=3,
                        minSize=(20, 20)
                    )

                    # If Haar doesn't detect a face, use the whole crop directly
                    if len(faces) > 0:
                        x, y, fw, fh = faces[0]
                        face_img = crop[y:y+fh, x:x+fw]
                    else:
                        face_img = crop

                    if face_img.size == 0:
                        continue

                    # -- Age & Gender inference ---------------
                    face_blob = cv2.dnn.blobFromImage(
                        face_img, 1.0, (227, 227),
                        _MODEL_MEAN, swapRB=False
                    )

                    self._gender_net.setInput(face_blob)
                    gender_preds = self._gender_net.forward()
                    gender = _GENDER_LABELS[gender_preds[0].argmax()]

                    self._age_net.setInput(face_blob)
                    age_preds = self._age_net.forward()
                    age_group = _AGE_BUCKETS[age_preds[0].argmax()]

                    ages.append(age_group)
                    genders.append(gender)

                except Exception:
                    continue

            with self._lock:
                self._age_history.extend(ages)
                self._gender_history.extend(genders)
                self._update_latest_results()

        finally:
            self._processing = False

    def _update_latest_results(self):
        """Calculate the distribution from history. Call with lock."""
        age_counts    = Counter(self._age_history)
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
            "last_update":  time.strftime("%H:%M:%S"),
        }

    def get_results(self) -> Dict:
        """Fetch the latest results. Thread-safe."""
        with self._lock:
            return dict(self._latest_results)

    @property
    def is_enabled(self) -> bool:
        return self._enabled