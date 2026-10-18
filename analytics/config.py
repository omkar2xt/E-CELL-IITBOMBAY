# config.py - analytics module
# ============================================================
# Extends tracking/config.py with settings for
# heatmap, queue monitoring, and demographic estimation.
# ============================================================

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Re-use all configs from tracking (which already include detection)
from tracking.config import (
    MODEL_NAME, CONFIDENCE_THRESHOLD, CLASS_PERSON,
    VIDEO_SOURCE, DISPLAY_FPS, DISPLAY_COUNT, DISPLAY_CONFIDENCE,
    BOX_COLOR, TEXT_COLOR, INFO_BG_COLOR, BOX_THICKNESS, FONT_SCALE,
    SAVE_OUTPUT, TRACK_THRESH, MATCH_THRESH, TRACK_BUFFER, FRAME_RATE,
    LINE_START, LINE_END, LINE_ORIENTATION, LINE_CROSSING_TOLERANCE,
    TRACK_ID_COLOR, LINE_COLOR, LINE_COLOR_ALERT,
    TRAJECTORY_COLOR, TRAJECTORY_LENGTH,
)

# -- Override --
WINDOW_NAME = "StorePulse AI - Analytics"
OUTPUT_PATH = "output_analytics.mp4"

# ============================================================
# HEATMAP
# ============================================================

# How much "heat" is added per person per frame
# Larger value = heatmap saturates faster (good for short videos)
# Smaller value = gradual accumulation (good for long videos / livestreams)
HEATMAP_INTENSITY = 3

# Gaussian kernel radius in pixels
# Large radius = wider "hot" area per person
# Small radius = more precise but granular accumulation
HEATMAP_RADIUS = 25

# How transparent the heatmap overlay is on top of the original frame
# 0.0 = invisible, 1.0 = full heatmap covering the frame
HEATMAP_ALPHA = 0.45

# OpenCV colormap for the heatmap
# cv2.COLORMAP_JET    : blue -> green -> yellow -> red (classic)
# cv2.COLORMAP_INFERNO: black -> purple -> orange -> white (more modern)
# cv2.COLORMAP_HOT    : black -> red -> yellow -> white
import cv2
HEATMAP_COLORMAP = cv2.COLORMAP_JET

# How often the heatmap is normalized (in frames)
# Normalizing too often = expensive, too rarely = early saturation
HEATMAP_NORMALIZE_INTERVAL = 15

# ============================================================
# QUEUE MONITORING
# ============================================================

# Cashier / queue zone.
# Format: (x1, y1, x2, y2) as frame RATIO (0.0 - 1.0)
# Using ratios means you don't need to change it if the video resolution is different.
#
# Default: Cashier area on the left (matching retail CCTV video)
# Change the numbers below based on the queue position if using another video.
# (x1=left, y1=top, x2=right, y2=bottom)
QUEUE_ZONE = (0.13, 0.15, 0.37, 0.50)
# QUEUE_ZONE = (0.65, 0.60, 1.0, 1.0)

# Threshold number of people in the cashier zone to trigger an alert
QUEUE_ALERT_THRESHOLD = 3

# Cashier zone colors
QUEUE_ZONE_COLOR       = (0, 255, 180)   # Cyan-green for normal
QUEUE_ZONE_COLOR_ALERT = (0, 60, 255)    # Red during alert
QUEUE_ZONE_ALPHA       = 0.25            # Transparency of the zone fill

# ============================================================
# DEMOGRAPHIC ESTIMATION
# ============================================================

# How often demographic estimation is run (in frames)
# The estimation can be slow, so don't run it every frame - run every N frames
DEMO_ANALYSIS_INTERVAL = 15

# Minimum face detection confidence before passing to estimation
DEMO_MIN_FACE_CONFIDENCE = 0.5

# Minimum bounding box height of a person (pixels) before trying face analysis
# Faces that are too small in the frame will produce inaccurate estimates
DEMO_MIN_PERSON_HEIGHT = 80

# Backend for face detection (before age/gender analysis)
# "opencv"      : fastest, medium accuracy
# "retinaface"  : more accurate but slower
# "mtcnn"       : balanced
DEMO_DETECTOR_BACKEND = "opencv"

# How many past analysis results to keep for aggregate statistics
# (rolling window for the demographics chart)
DEMO_HISTORY_SIZE = 50

# Demographic label color above the bounding box
DEMO_LABEL_COLOR = (255, 180, 50)

# ============================================================
# DISPLAY
# ============================================================

# Info panel on the bottom right for demographics
DEMO_PANEL_WIDTH  = 220
DEMO_PANEL_HEIGHT = 160