# heatmap.py
# ============================================================
# Akumulasi posisi foot traffic menjadi heatmap.
#
# Cara kerja:
# 1. Maintain numpy array 2D berukuran sama dengan frame
# 2. Setiap orang terdeteksi -> tambahkan Gaussian "blob" di posisinya
# 3. Normalize array -> apply colormap -> overlay ke frame
#
# Kenapa Gaussian dan bukan dot biasa?
# Gaussian membuat area di sekitar orang ikut "panas" secara gradual,
# bukan hanya satu pixel. Ini lebih realistis karena orang menempati
# area, bukan titik.
# ============================================================

import cv2
import numpy as np
from typing import List, Tuple
import config


class HeatmapGenerator:

    def __init__(self, frame_width: int, frame_height: int):
        self.width  = frame_width
        self.height = frame_height

        # Akumulator utama - float32 supaya bisa akumulasi nilai besar
        # tanpa overflow (uint8 max = 255)
        self._accumulator = np.zeros((frame_height, frame_width), dtype=np.float32)

        # Pre-compute Gaussian kernel sekali saja supaya tidak compute ulang
        # tiap frame (optimasi)
        self._kernel = self._make_gaussian_kernel(config.HEATMAP_RADIUS)

        self._frame_count = 0

        print(f"[Heatmap] Init {frame_width}x{frame_height}, "
              f"radius={config.HEATMAP_RADIUS}, intensity={config.HEATMAP_INTENSITY}")

    def _make_gaussian_kernel(self, radius: int) -> np.ndarray:
        """
        Buat Gaussian kernel 2D.

        Kernel ini adalah "stempel" yang ditempel ke accumulator
        setiap ada orang. Bentuknya seperti bukit: puncak di tengah,
        menurun ke tepi.

        radius: menentukan seberapa besar area yang terpengaruh.
        """
        size = radius * 2 + 1
        x = np.linspace(-radius, radius, size)
        gauss_1d = np.exp(-0.5 * (x / (radius / 2)) ** 2)
        kernel = np.outer(gauss_1d, gauss_1d)
        # Normalize supaya total energi = 1
        kernel = kernel / kernel.sum()
        return kernel.astype(np.float32)

    def update(self, positions: List[Tuple[int, int]]):
        """
        Tambahkan posisi orang ke accumulator.

        Args:
            positions: list titik (cx, cy) dari setiap tracked person
        """
        self._frame_count += 1
        r = config.HEATMAP_RADIUS
        kh, kw = self._kernel.shape
        intensity = config.HEATMAP_INTENSITY

        for cx, cy in positions:
            # Hitung area di accumulator yang akan ditempel kernel
            x1 = cx - r
            y1 = cy - r
            x2 = cx + r + 1
            y2 = cy + r + 1

            # Hitung overlap antara kernel dan batas frame
            # (kalau orang di tepi frame, kernel mungkin keluar batas)
            kx1 = max(0, -x1)
            ky1 = max(0, -y1)
            kx2 = kw - max(0, x2 - self.width)
            ky2 = kh - max(0, y2 - self.height)

            ax1 = max(0, x1)
            ay1 = max(0, y1)
            ax2 = min(self.width,  x2)
            ay2 = min(self.height, y2)

            # Validasi area overlap tidak kosong
            if ax2 > ax1 and ay2 > ay1 and kx2 > kx1 and ky2 > ky1:
                self._accumulator[ay1:ay2, ax1:ax2] += (
                    self._kernel[ky1:ky2, kx1:kx2] * intensity
                )

    def get_overlay(self) -> np.ndarray:
        """
        Kembalikan heatmap sebagai BGR image siap di-overlay.

        Normalize accumulator -> apply colormap -> return BGR array.
        """
        if self._accumulator.max() == 0:
            # Belum ada data, return black image
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # Normalize ke 0-255
        normalized = cv2.normalize(
            self._accumulator, None,
            0, 255,
            cv2.NORM_MINMAX
        ).astype(np.uint8)

        # Apply colormap
        colored = cv2.applyColorMap(normalized, config.HEATMAP_COLORMAP)

        return colored

    def apply_to_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Blend heatmap overlay ke atas frame.

        Hanya pixel yang "panas" (nilai > threshold) yang di-overlay,
        area kosong tetap menampilkan frame asli.
        """
        overlay = self.get_overlay()

        # Mask: hanya area yang punya nilai signifikan
        if self._accumulator.max() > 0:
            normalized = cv2.normalize(
                self._accumulator, None, 0, 255, cv2.NORM_MINMAX
            ).astype(np.uint8)

            # Threshold: hanya area > 10% dari max yang di-overlay
            _, mask = cv2.threshold(normalized, 25, 255, cv2.THRESH_BINARY)
            mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            mask_norm = mask_3ch.astype(np.float32) / 255.0

            # Blend hanya di area mask
            alpha = config.HEATMAP_ALPHA
            blended = frame.copy().astype(np.float32)
            blended = np.where(
                mask_3ch > 0,
                frame.astype(np.float32) * (1 - alpha) + overlay.astype(np.float32) * alpha,
                frame.astype(np.float32)
            )
            return blended.astype(np.uint8)

        return frame

    def reset(self):
        """Reset accumulator (misal untuk sesi baru)."""
        self._accumulator[:] = 0
        self._frame_count = 0

    @property
    def frame_count(self) -> int:
        return self._frame_count