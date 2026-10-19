# StorePulse AI — Setup & Initialization Guide

**Document:** Setup & Initialization Guide  
**Author:** Omkar Gurav  
**Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator  
**Version:** 1.0.0  

---

## 1. Prerequisites & System Requirements

### 1.1 Supported Operating Systems
- **Windows:** Windows 10 / 11 (64-bit) — *Verified on Windows 11 AMD64*.
- **Linux:** Ubuntu 20.04+, Debian 11+, RHEL 8+.
- **macOS:** macOS Monterey (12.0+) with Apple Silicon (M1/M2/M3) or Intel.

### 1.2 Software Dependencies
- **Python:** 3.10, 3.11, 3.12, 3.13, or 3.14 (Verified on Python 3.14.3).
- **Node.js:** v18.0.0 or higher (Verified on Node.js v24.14.0 / npm v10.8.2).
- **Git:** Version 2.30+.
- **Hardware:**
  - Minimum: 4-Core x86_64 or ARM64 CPU, 8 GB RAM.
  - Recommended: 8-Core CPU or NVIDIA GPU with CUDA 11.8+ for 30 FPS multi-stream processing.

---

## 2. Step-by-Step Installation

### Step 1: Clone Repository
```bash
git clone https://github.com/omkargurav/storepulse-ai.git
cd storepulse-ai
```

### Step 2: Environment Configuration
Create your local environment file by copying the template:
```bash
# Linux / macOS
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

**Key `.env` Configuration Options:**
```ini
# Path to video file OR webcam index (0, 1) OR rtsp:// URL
VIDEO_SOURCE=detection/vid/retail-cctv-footage.mp4

# Host and Port
HOST=0.0.0.0
PORT=8000

# Broadcast interval (frames between WebSocket telemetry packets)
BROADCAST_INTERVAL=5

# Privacy Settings (Keep false for default privacy compliance)
DEMOGRAPHICS_ENABLED=false

# Zone Defaults
QUEUE_ALERT_THRESHOLD=3
TRACKING_RETENTION_SECONDS=3600
```

---

### Step 3: Python Backend Installation
It is recommended to use a Python virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows Command Prompt:
.\venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

**Verified Python Package Versions:**
- `ultralytics>=8.3.0` (YOLO11n person detection)
- `torch>=2.0.0`
- `opencv-python>=4.8.0`
- `fastapi>=0.110.0`
- `uvicorn[standard]>=0.28.0`
- `pydantic>=2.6.0`
- `lap==0.5.13` (Linear assignment for ByteTrack)
- `pytest>=8.0.0`

---

### Step 4: Frontend Dashboard Installation
```bash
cd dashboard
npm install
cd ..
```

---

## 3. Running the System Locally

### Step 1: Launch FastAPI Backend
In your first terminal (with virtual environment active):
```bash
python backend/main.py
```
**Expected Console Output:**
```text
[Pipeline] Loading model: yolo11n.pt
[Pipeline] ByteTrack ready. Buffer: 30 frames, Thresh: 0.4
[StorePulse AI] Starting analytics pipeline...
[Pipeline] Started background thread (source: detection/vid/retail-cctv-footage.mp4)
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```
- API Documentation (Swagger): `http://localhost:8000/docs`
- Live MJPEG Stream: `http://localhost:8000/snapshot`
- Live WebSocket: `ws://localhost:8000/ws`

### Step 2: Launch React Dashboard
In a second terminal:
```bash
cd dashboard
npm run dev
```
**Expected Console Output:**
```text
  VITE v6.4.4  ready in 320 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```
- Open `http://localhost:5173` in your web browser.

---

## 4. Validating the Installation

### 4.1 Execute Backend Test Suite
```bash
python -m pytest tests -v
```
- Expected Result: **46 passed in ~12 seconds (100% pass rate)**.

### 4.2 Execute Frontend Production Build
```bash
cd dashboard
npm run build
```
- Expected Result: **Exit Code 0 (0 errors, built in ~10s)**.

### 4.3 Run End-to-End Workflow Verification Script
```bash
python scripts/verify_phase4_workflow.py
```
- Expected Result: **All 8 workflow steps execute and record transcript to `docs/workflow_execution_transcript.json`**.
