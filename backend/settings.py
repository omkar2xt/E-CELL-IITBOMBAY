import os

# Video source path relative to backend directory
# Defaulting to the same video used in analytics
VIDEO_SOURCE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'detection', 'vid', 'retail-cctv-footage.mp4'))

# How often to broadcast metrics via WebSocket (in frames)
BROADCAST_INTERVAL = 5

# Port for FastAPI server
PORT = 8000
HOST = "0.0.0.0"
