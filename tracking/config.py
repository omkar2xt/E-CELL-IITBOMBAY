# config.py - tracking module
# ============================================================
# Extends detection/config.py with additional
# settings for tracking and counting.
# ============================================================

import sys
import os

# To be able to import from detection/ folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# -- Import all detection configs (re-use) --
from detection.config import (
    MODEL_NAME,
    CONFIDENCE_THRESHOLD,
    CLASS_PERSON,
    VIDEO_SOURCE,
    DISPLAY_FPS,
    DISPLAY_COUNT,
    DISPLAY_CONFIDENCE,
    BOX_COLOR,
    TEXT_COLOR,
    INFO_BG_COLOR,
    BOX_THICKNESS,
    FONT_SCALE,
    SAVE_OUTPUT,
)

# -- Override --
WINDOW_NAME = "Retail Analytics - Week 2: Tracking + Counting"
OUTPUT_PATH = "output_week2.mp4"

# -- ByteTrack settings --
# track_thresh: minimum confidence to directly assign to an active track
# Detections below this fall into "second association" (ByteTrack trick)
TRACK_THRESH = 0.4

# match_thresh: minimum IoU to be considered "the same person"
MATCH_THRESH = 0.8

# track_buffer: how many frames a track "survives" without detection
# Before it's considered lost and its ID is discarded
# 30 frames = ~1 second at 30fps. Increase if people often disappear briefly.
TRACK_BUFFER = 30

# frame_rate: input video FPS (used by Kalman for motion prediction)
FRAME_RATE = 30

# -- Virtual Line Counting --
# Virtual line for counting people entering/exiting.
# Format: (x1, y1, x2, y2) in pixels
#
# How to determine position:
# - For horizontal entrance: vertical line in the middle of the frame
#   LINE_START = (frame_width // 2, 0)
#   LINE_END   = (frame_width // 2, frame_height)
#
# - For vertical entrance: horizontal line in the middle of the frame
#   LINE_START = (0, frame_height // 2)
#   LINE_END   = (frame_width, frame_height // 2)
#
# Default below: vertical line in the middle of a 640px frame
# Will be automatically overridden in main.py based on actual video resolution
LINE_START = (320, 0)
LINE_END   = (320, 480)

# Which direction is counted as "in" vs "out"
# "horizontal": people moving left-right crossing a vertical line
#   - moving RIGHT = in (IN)
#   - moving LEFT  = out (OUT)
# "vertical": people moving up-down crossing a horizontal line
#   - moving DOWN = in (IN)
#   - moving UP   = out (OUT)
LINE_ORIENTATION = "horizontal"

# Width of "dead zone" around the line (pixels)
# A person must completely cross the line (not just touch it)
# before the crossing is counted. Prevents false counts.
LINE_CROSSING_TOLERANCE = 5

# -- Additional colors for tracking --
TRACK_ID_COLOR    = (255, 220, 50)   # Yellow for Track ID label
LINE_COLOR        = (0, 200, 255)    # Cyan for virtual line
LINE_COLOR_ALERT  = (0, 60, 255)     # Red when there's a crossing event
TRAJECTORY_COLOR  = (180, 180, 180)  # Gray for movement trail
TRAJECTORY_LENGTH = 30               # How many past frames of the trail to display