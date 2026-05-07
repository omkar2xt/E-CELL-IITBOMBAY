# heatmap.py
# ============================================================
# Accumulates foot traffic positions into a heatmap.
#
# How it works:
# 1. Maintain a 2D numpy array the same size as the frame
# 2. Each time a person is detected -> add a Gaussian "blob" at their position
# 3. Normalize the array -> apply colormap -> overlay onto the frame
#
# Why a Gaussian and not just a normal dot?
# A Gaussian makes the area around the person also "hot" gradually,
# not just a single pixel. This is more realistic because a person occupies
# an area, not a point.
# ============================================================

import cv2
import numpy as np
from typing import List, Tuple
import config


class HeatmapGenerator:

    def __init__(self, frame_width: int, frame_height: int):
        self.width  = frame_width
        self.height = frame_height

        # Main accumulator - float32 so it can accumulate large values
        # without overflowing (uint8 max = 255)
        self._accumulator = np.zeros((frame_height, frame_width), dtype=np.float32)

        # Pre-compute the Gaussian kernel once so it doesn't need recomputing
        # every frame (optimization)
        self._kernel = self._make_gaussian_kernel(config.HEATMAP_RADIUS)

        self._frame_count = 0

        print(f"[Heatmap] Init {frame_width}x{frame_height}, "
              f"radius={config.HEATMAP_RADIUS}, intensity={config.HEATMAP_INTENSITY}")

    def _make_gaussian_kernel(self, radius: int) -> np.ndarray:
        """
        Create a 2D Gaussian kernel.

        This kernel is like a "stamp" pasted onto the accumulator
        for every person. Its shape is like a hill: peak at the center,
        sloping down to the edges.

        radius: determines how large the affected area is.
        """
        size = radius * 2 + 1
        x = np.linspace(-radius, radius, size)
        gauss_1d = np.exp(-0.5 * (x / (radius / 2)) ** 2)
        kernel = np.outer(gauss_1d, gauss_1d)
        # Normalize so total energy = 1
        kernel = kernel / kernel.sum()
        return kernel.astype(np.float32)

    def update(self, positions: List[Tuple[int, int]]):
        """
        Add people's positions to the accumulator.

        Args:
            positions: list of (cx, cy) points for each tracked person
        """
        self._frame_count += 1
        r = config.HEATMAP_RADIUS
        kh, kw = self._kernel.shape
        intensity = config.HEATMAP_INTENSITY

        for cx, cy in positions:
            # Calculate the area on the accumulator where the kernel will be placed
            x1 = cx - r
            y1 = cy - r
            x2 = cx + r + 1
            y2 = cy + r + 1

            # Calculate the overlap between the kernel and the frame boundaries
            # (if the person is at the edge of the frame, the kernel might go out of bounds)
            kx1 = max(0, -x1)
            ky1 = max(0, -y1)
            kx2 = kw - max(0, x2 - self.width)
            ky2 = kh - max(0, y2 - self.height)

            ax1 = max(0, x1)
            ay1 = max(0, y1)
            ax2 = min(self.width,  x2)
            ay2 = min(self.height, y2)

            # Validate that the overlap area is not empty
            if ax2 > ax1 and ay2 > ay1 and kx2 > kx1 and ky2 > ky1:
                self._accumulator[ay1:ay2, ax1:ax2] += (
                    self._kernel[ky1:ky2, kx1:kx2] * intensity
                )

    def get_overlay(self) -> np.ndarray:
        """
        Return the heatmap as a BGR image ready to be overlaid.

        Normalize accumulator -> apply colormap -> return BGR array.
        """
        if self._accumulator.max() == 0:
            # No data yet, return a black image
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # Normalize to 0-255
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
        Blend the heatmap overlay onto the frame.

        Only "hot" pixels (values > threshold) are overlaid,
        empty areas continue to show the original frame.
        """
        overlay = self.get_overlay()

        # Mask: only areas with significant values
        if self._accumulator.max() > 0:
            normalized = cv2.normalize(
                self._accumulator, None, 0, 255, cv2.NORM_MINMAX
            ).astype(np.uint8)

            # Threshold: only areas > 10% of max are overlaid
            _, mask = cv2.threshold(normalized, 25, 255, cv2.THRESH_BINARY)
            mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            mask_norm = mask_3ch.astype(np.float32) / 255.0

            # Blend only in the masked areas
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
        """Reset the accumulator (e.g., for a new session)."""
        self._accumulator[:] = 0
        self._frame_count = 0

    @property
    def frame_count(self) -> int:
        return self._frame_count