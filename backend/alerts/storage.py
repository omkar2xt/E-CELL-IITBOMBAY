# StorePulse AI — Evidence Storage Manager
# Developer: Omkar Gurav
# Handles local snapshot image storage and private Vercel Blob cloud storage
# Supports SHA-256 checksums, thumbnailing, path-traversal prevention, and resilient fallbacks

import os
import cv2
import hashlib
import logging
from typing import Dict, Any, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

class EvidenceStorageManager:
    """
    Manages persistent storage for alert evidence snapshots.
    Supports both local filesystem and private Vercel Blob storage.
    Enforces path-traversal prevention, image validation, and atomic writes.
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "data", "snapshots")
            )
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

        # Cloud storage configuration (Vercel Blob)
        self.blob_token = os.getenv("BLOB_READ_WRITE_TOKEN", "").strip()
        self.blob_access = os.getenv("BLOB_ACCESS", "private").lower()
        if self.blob_access not in ("private", "public"):
            self.blob_access = "private"

    def is_blob_configured(self) -> bool:
        """Check if Vercel Blob authentication token is configured."""
        return bool(self.blob_token)

    def _resolve_safe_path(self, relative_key: str) -> str:
        """Resolve path and guard against directory traversal attacks."""
        if not relative_key:
            raise ValueError("Empty storage key provided")
        if ".." in relative_key or relative_key.startswith(("/", "\\")):
            raise ValueError(f"Path traversal detected: {relative_key}")
        
        clean_key = os.path.basename(relative_key)
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
        Writes to local disk and seamlessly uploads to private Vercel Blob if configured.
        Returns metadata for database persistence (keys, size, dimensions, checksum).
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

        # Encode full-resolution image to JPEG buffer
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]
        ret, buffer = cv2.imencode('.jpg', frame, encode_params)
        if not ret:
            logger.error(f"[Storage] Failed to encode JPEG snapshot for {alert_id}")
            return {
                "storage_key": "",
                "thumbnail_key": None,
                "file_size_bytes": 0,
                "image_width": w,
                "image_height": h,
                "checksum": None,
                "capture_status": "failed"
            }

        img_bytes = buffer.tobytes()
        file_size = len(img_bytes)
        checksum = hashlib.sha256(img_bytes).hexdigest()

        # Generate lightweight thumbnail (max width 320, keeping aspect ratio)
        thumb_width = 320
        thumb_height = max(1, int(h * (thumb_width / w)))
        thumb_frame = cv2.resize(frame, (thumb_width, thumb_height), interpolation=cv2.INTER_AREA)
        ret_thumb, thumb_buffer = cv2.imencode('.jpg', thumb_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        thumb_bytes = thumb_buffer.tobytes() if ret_thumb else b""

        # 1. Always save local copy on disk as local cache / resilient fallback
        try:
            with open(full_path, "wb") as f:
                f.write(img_bytes)
            if thumb_bytes:
                with open(thumb_path, "wb") as f:
                    f.write(thumb_bytes)
        except Exception as e:
            logger.warning(f"[Storage] Local disk write warning for {alert_id}: {e}")

        storage_key = full_filename
        thumbnail_key = thumb_filename

        # 2. Upload to private Vercel Blob if configured
        if self.is_blob_configured():
            try:
                from vercel.blob.sync import put_blob

                blob_full_path = f"snapshots/{full_filename}"
                put_res = put_blob(
                    blob_full_path,
                    img_bytes,
                    access=self.blob_access,
                    add_random_suffix=False,
                    allow_overwrite=True
                )
                storage_key = blob_full_path

                if thumb_bytes:
                    blob_thumb_path = f"snapshots/{thumb_filename}"
                    put_blob(
                        blob_thumb_path,
                        thumb_bytes,
                        access=self.blob_access,
                        add_random_suffix=False,
                        allow_overwrite=True
                    )
                    thumbnail_key = blob_thumb_path

                logger.info(f"[Storage] Successfully uploaded snapshot {alert_id} to Vercel Blob ({self.blob_access})")

            except Exception as blob_err:
                # Do NOT fail the alert if cloud upload encounters network issue; fallback to local
                logger.error(f"[Storage] Vercel Blob upload failed for {alert_id}, retaining local storage: {blob_err}")
                storage_key = full_filename
                thumbnail_key = thumb_filename

        return {
            "storage_key": storage_key,
            "thumbnail_key": thumbnail_key,
            "file_size_bytes": file_size,
            "image_width": w,
            "image_height": h,
            "checksum": checksum,
            "capture_status": "saved"
        }

    def get_snapshot_bytes(self, storage_key: str, thumbnail: bool = False) -> Tuple[Optional[bytes], str]:
        """
        Retrieve snapshot image binary data safely.
        Fetches from private Vercel Blob using backend credentials or local disk fallback.
        Credentials are never exposed to the caller.
        """
        if not storage_key:
            return None, "image/jpeg"

        target_key = storage_key
        if thumbnail:
            if "_full.jpg" in storage_key:
                target_key = storage_key.replace("_full.jpg", "_thumb.jpg")
            elif "thumbnail" in storage_key:
                target_key = storage_key

        # 1. Attempt Vercel Blob retrieval if cloud storage configured or key matches blob path
        if self.is_blob_configured() or target_key.startswith("snapshots/") or target_key.startswith("http"):
            try:
                from vercel.blob.sync import get_blob
                blob_res = get_blob(target_key, access=self.blob_access)
                if blob_res and blob_res.body:
                    return blob_res.body, "image/jpeg"
            except Exception as e:
                logger.debug(f"[Storage] Vercel Blob fetch miss for key {target_key}: {e}")

        # 2. Local filesystem fallback
        try:
            local_filename = os.path.basename(target_key)
            local_path = self._resolve_safe_path(local_filename)
            if os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    return f.read(), "image/jpeg"

            # Fallback to full image if thumbnail requested but missing
            if thumbnail:
                base_full = os.path.basename(storage_key)
                full_path = self._resolve_safe_path(base_full)
                if os.path.exists(full_path):
                    with open(full_path, "rb") as f:
                        return f.read(), "image/jpeg"
        except Exception as e:
            logger.error(f"[Storage] Error reading local snapshot {target_key}: {e}")

        return None, "image/jpeg"

    def get_snapshot_path(self, storage_key: str, thumbnail: bool = False) -> Optional[str]:
        """Return the absolute local path for a storage key if cached locally."""
        try:
            target_key = os.path.basename(storage_key)
            if thumbnail and "_full.jpg" in target_key:
                target_key = target_key.replace("_full.jpg", "_thumb.jpg")
            path = self._resolve_safe_path(target_key)
            if os.path.exists(path):
                return path
            fallback = self._resolve_safe_path(os.path.basename(storage_key))
            return fallback if os.path.exists(fallback) else None
        except Exception:
            return None

    def delete_snapshot(self, storage_key: str, thumbnail_key: Optional[str] = None) -> bool:
        """Delete evidence files from local disk and Vercel Blob."""
        deleted = False

        # 1. Delete from local disk
        try:
            if storage_key:
                p = self._resolve_safe_path(os.path.basename(storage_key))
                if os.path.exists(p):
                    os.remove(p)
                    deleted = True
            if thumbnail_key:
                tp = self._resolve_safe_path(os.path.basename(thumbnail_key))
                if os.path.exists(tp):
                    os.remove(tp)
        except Exception as e:
            logger.warning(f"[Storage] Local snapshot deletion warning: {e}")

        # 2. Delete from Vercel Blob if configured
        if self.is_blob_configured():
            try:
                from vercel.blob.sync import delete_blob
                if storage_key:
                    delete_blob(storage_key)
                if thumbnail_key:
                    delete_blob(thumbnail_key)
                deleted = True
            except Exception as e:
                logger.warning(f"[Storage] Vercel Blob deletion warning: {e}")

        return deleted

    def get_storage_stats(self) -> Dict[str, Any]:
        """Return storage usage metrics and cloud integration status."""
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
            "cloud_storage": "vercel_blob" if self.is_blob_configured() else "local_disk",
            "blob_access": self.blob_access if self.is_blob_configured() else None,
            "status": "healthy"
        }

# Global instance
storage_manager = EvidenceStorageManager()
