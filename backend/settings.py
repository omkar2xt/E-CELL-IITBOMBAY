# StorePulse AI — Backend Settings
# Developer: Omkar Gurav

import os
from dotenv import load_dotenv

load_dotenv()

def _resolve_video_source(raw: str) -> str:
    """Return int for webcam index, absolute path string for files."""
    try:
        return int(raw)
    except (ValueError, TypeError):
        # Try relative to project root first
        abs_path = os.path.abspath(raw)
        if not os.path.exists(abs_path):
            # Fall back to path relative to this file's parent
            abs_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', raw)
            )
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
