# StorePulse AI — Vercel Serverless Function Entry Point
# Developer: Omkar Gurav
# Exports FastAPI app for @vercel/python runtime

import os
import sys

# Ensure project root is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Enforce serverless environment flags
os.environ["SERVERLESS"] = "1"
os.environ["VERCEL"] = "1"

# Import ASGI application
from backend.main import app
