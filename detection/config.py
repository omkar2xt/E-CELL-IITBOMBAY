# config.py
# ============================================================
# All project configurations are defined here.
# If you want to change a setting, just edit this file.
# ============================================================

# --- Model ---
MODEL_NAME = "yolo11n.pt"        # n=nano (lightest & fastest)
                                 # Other options: yolo11s.pt, yolo11m.pt, yolo11l.pt
                                 # Larger model = more accurate but slower
                                 # For development, stick with nano

# --- Detection ---
CONFIDENCE_THRESHOLD = 0.4       # Minimum confidence to be considered "person"
                                 # 0.4 = 40%. Too low -> many false positives
                                 #            Too high -> misses people (false negatives)
                                 # For retail indoor, 0.35-0.5 is usually good

CLASS_PERSON = 0                 # In COCO dataset, class index 0 = "person"
                                 # YOLO automatically filters, so only people are detected

# --- Video Input ---
# Change to your video path, or 0 for webcam
# Example: VIDEO_SOURCE = "data/mall_sample.mp4"
# Example: VIDEO_SOURCE = 0   <- default webcam
VIDEO_SOURCE = 0                 # Default: webcam

# --- Display ---
WINDOW_NAME = "Retail Analytics - Week 1: Detection"
DISPLAY_FPS = True               # Show FPS in the top left corner
DISPLAY_COUNT = True             # Show number of detected people
DISPLAY_CONFIDENCE = True        # Show confidence score on each box

# Bounding box color (BGR format, not RGB!)
# BGR: (Blue, Green, Red)
BOX_COLOR = (0, 255, 100)        # Bright green
TEXT_COLOR = (255, 255, 255)     # White
INFO_BG_COLOR = (0, 0, 0)        # Black text background
BOX_THICKNESS = 2
FONT_SCALE = 0.55

# --- Output (optional) ---
SAVE_OUTPUT = False              # Set True if you want to save the output video
OUTPUT_PATH = "output_week1.mp4"