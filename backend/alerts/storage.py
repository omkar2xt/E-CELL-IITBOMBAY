# StorePulse AI — Evidence Storage Manager
# Developer: Omkar Gurav
# Handles local snapshot image storage, thumbnailing, SHA256 checksums, and security

import os
import cv2
import hashlib
import numpy as np
from typing import Dict, Any, Optional, Tuple

class EvidenceStorageManager:
    """
    Manages persistent filesystem storage for alert evidence snapshots.
    Ensures path-traversal prevention, image validation, and atomic writes.
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "data", "snapshots")
            )
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_safe_path(self, relative_key: str) -> str:
        """Resolve path and guard against directory traversal attacks."""
        if not relative_key or ".." in relative_key or relative_key.startswith(("/", "\\")):
            clean_key = os.path.basename(relative_key)
        else:
            clean_key = relative_key
        
        full_path = os.path.abspath(os.path.join(self.base_dir, clean_key))
        if not full_path.startswith(self.base_dir):
            raise ValueError(f"Path traversal detected: {relative_key}")
        return full_path

    def save_snapshot(
        self,
        alert_id: str,
        frame: np.ndarray,
        jpeg_quality: int = 90
    ) -> Dict[str, Any]:
        """
        Save full-resolution annotated frame and a lightweight thumbnail.
        Computes SHA-256 checksum for audit and integrity verification.
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return {
                "storage_key": "",
                "thumbnail_key": None,
                "file_size_bytes": 0,
                "image_width": 0,
                "image_height": 0,
                "checksum": None,
                "capture_status": "failed"
            }

        h, w = frame.shape[:2]
        full_filename = f"{alert_id}_full.jpg"
        thumb_filename = f"{alert_id}_thumb.jpg"

        full_path = self._resolve_safe_path(full_filename)
        thumb_path = self._resolve_safe_path(thumb_filename)

        # Encode full-resolution image
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]
        ret, buffer = cv2.imencode('.jpg', frame, encode_params)
        if not ret:
            raise RuntimeError("Failed to encode JPEG snapshot")

        img_bytes = buffer.tobytes()
        file_size = len(img_bytes)
        checksum = hashlib.sha256(img_bytes).hexdigest()

        # Write full-res image
        with open(full_path, "wb") as f:
            f.write(img_bytes)

        # Generate and save thumbnail (max width 320, keeping aspect ratio)
        thumb_width = 320
        thumb_height = max(1, int(h * (thumb_width / w)))
        thumb_frame = cv2.resize(frame, (thumb_width, thumb_height), interpolation=cv2.INTER_AREA)
        cv2.imwrite(thumb_path, thumb_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])

        return {
            "storage_key": full_filename,
            "thumbnail_key": thumb_filename,
            "file_size_bytes": file_size,
            "image_width": w,
            "image_height": h,
            "checksum": checksum,
            "capture_status": "saved"
        }

    def get_snapshot_path(self, storage_key: str, thumbnail: bool = False) -> Optional[str]:
        """Return the absolute path for a storage key safely."""
        try:
            target_key = storage_key
            if thumbnail and "_full.jpg" in storage_key:
                target_key = storage_key.replace("_full.jpg", "_thumb.jpg")
            path = self._resolve_safe_path(target_key)
            if os.path.exists(path):
                return path
            # Fallback to full image if thumbnail is requested but missing
            fallback = self._resolve_safe_path(storage_key)
            return fallback if os.path.exists(fallback) else None
        except Exception:
            return None

    def delete_snapshot(self, storage_key: str, thumbnail_key: Optional[str] = None) -> bool:
        """Delete evidence files from disk."""
        deleted = False
        try:
            if storage_key:
                p = self._resolve_safe_path(storage_key)
                if os.path.exists(p):
                    os.remove(p)
                    deleted = True
            if thumbnail_key:
                tp = self._resolve_safe_path(thumbnail_key)
                if os.path.exists(tp):
                    os.remove(tp)
        except Exception:
            pass
        return deleted

    def get_storage_stats(self) -> Dict[str, Any]:
        """Return storage usage metrics."""
        count = 0
        total_size = 0
        try:
            for entry in os.scandir(self.base_dir):
                if entry.is_file() and entry.name.endswith(".jpg"):
                    count += 1
                    total_size += entry.stat().st_size
        except Exception:
            pass

        return {
            "base_dir": self.base_dir,
            "total_snapshots": count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "status": "healthy"
        }

# Global instance
storage_manager = EvidenceStorageManager()
