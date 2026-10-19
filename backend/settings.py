# StorePulse AI — Backend Settings
# Developer: Omkar Gurav

import os
from dotenv import load_dotenv

load_dotenv()

def _resolve_video_source(raw: str):
    """
    Resolve video source configuration:
    - Integer: webcam index (e.g. 0, 1)
    - URL: RTSP or HTTP/HTTPS stream (e.g. rtsp://..., http://...)
    - Path: video file path (relative to root or absolute)
    """
    if raw is None:
        raw = os.path.join(os.path.dirname(__file__), '..', 'detection', 'vid', 'retail-cctv-footage.mp4')

    raw_str = str(raw).strip()

    # Numeric webcam index
    try:
        return int(raw_str)
    except (ValueError, TypeError):
        pass

    # RTSP / HTTP network video stream
    if raw_str.startswith(("rtsp://", "http://", "https://", "rtsps://")):
        return raw_str

    # File path resolution
    abs_path = os.path.abspath(raw_str)
    if os.path.exists(abs_path):
        return abs_path

    # Check relative to project root
    root_rel = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', raw_str))
    if os.path.exists(root_rel):
        return root_rel

    # Return normalized path if not yet created
    return abs_path


VIDEO_SOURCE = _resolve_video_source(
    os.getenv("VIDEO_SOURCE",
               os.path.join(os.path.dirname(__file__), '..', 'detection', 'vid', 'retail-cctv-footage.mp4'))
)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
BROADCAST_INTERVAL = int(os.getenv("BROADCAST_INTERVAL", 5))
DEMOGRAPHICS_ENABLED = os.getenv("DEMOGRAPHICS_ENABLED", "false").lower() == "true"
QUEUE_ALERT_THRESHOLD = int(os.getenv("QUEUE_ALERT_THRESHOLD", 3))
TRACKING_RETENTION_SECONDS = int(os.getenv("TRACKING_RETENTION_SECONDS", 3600))

# Camera Reconnection & Resilience Settings
CAMERA_RECONNECT_MAX_RETRIES = int(os.getenv("CAMERA_RECONNECT_MAX_RETRIES", 5))
CAMERA_RECONNECT_DELAY_BASE = float(os.getenv("CAMERA_RECONNECT_DELAY_BASE", 1.0))
CAMERA_RECONNECT_DELAY_MAX = float(os.getenv("CAMERA_RECONNECT_DELAY_MAX", 10.0))

