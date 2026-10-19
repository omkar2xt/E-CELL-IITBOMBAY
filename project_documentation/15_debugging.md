# StorePulse AI — Troubleshooting & Debugging Playbook

**Document Version:** 1.0.0  
**Author:** Omkar Gurav  
**Target:** DevOps Engineers, Computer Vision Developers, Store Technicians  

---

## 1. Quick Diagnostic Triage

When encountering an issue, execute this 30-second triage checklist:

```bash
# 1. Verify Python virtual environment is active
where python
# Expected: ...\E-cell-IIT-BOMBAY\venv\Scripts\python.exe

# 2. Check backend health endpoint
curl -s http://127.0.0.1:8000/health
# Expected: {"status":"healthy","pipeline_active":true,"fps":15.0}

# 3. Check active ports (8000 and 5173)
netstat -ano | findstr "8000 5173"

# 4. Inspect backend logs
Get-Content logs/storepulse.log -Tail 30
```

---

## 2. Common Error Signatures & Recovery Solutions

### Issue 1: `UnicodeEncodeError: 'charmap' codec can't encode character '\u2713'`
- **Symptom:** Scripts crash on Windows PowerShell/CMD when printing Unicode checkmarks (`✓`) or arrows (`→`).
- **Root Cause:** Default Windows console code page is `cp1252` instead of `utf-8`.
- **Solution:**
  1. Set environment variable before execution:
     ```powershell
     $env:PYTHONIOENCODING = "utf-8"
     ```
  2. In Python entrypoint scripts, add explicit stdout reconfiguration:
     ```python
     import sys
     if sys.platform == "win32":
         sys.stdout.reconfigure(encoding="utf-8")
     ```

---

### Issue 2: `[Errno 10048] Address already in use (Port 8000 or 5173)`
- **Symptom:** Uvicorn or Vite refuses to start with port conflict error.
- **Root Cause:** A orphaned background process from a previous session is still holding the socket.
- **Solution:**
  1. Find the conflicting Process ID (PID):
     ```powershell
     # For Backend (Port 8000)
     netstat -ano | findstr ":8000"
     # For Frontend (Port 5173)
     netstat -ano | findstr ":5173"
     ```
  2. Terminate the offending PID:
     ```powershell
     taskkill /PID <PID> /F
     ```
  3. Alternatively, specify an alternate port:
     ```bash
     uvicorn backend.main:app --port 8001
     ```

---

### Issue 3: Video Stream Disconnection / `cv2.VideoCapture` returns `None`
- **Symptom:** Backend starts, but live analytics report 0 tracks, FPS is 0.0, and `/health` reports `pipeline_active: false`.
- **Root Cause:** RTSP camera is unreachable, USB webcam is disconnected, or local MP4 path does not exist.
- **Diagnostic Steps:**
  ```python
  import cv2
  cap = cv2.VideoCapture("data/retail_demo.mp4")
  print("Opened:", cap.isOpened())
  ret, frame = cap.read()
  print("Frame captured:", ret, frame.shape if ret else "None")
  cap.release()
  ```
- **Recovery Solution:**
  1. If video file is missing, verify path exists relative to workspace root: `e:\ALL HACKTHONS\E-cell-IIT-BOMBAY\data\`.
  2. Enable automatic synthetic fallback mode in `backend/settings.py`:
     ```python
     FALLBACK_TO_SYNTHETIC = True
     ```
  3. For RTSP cameras, ensure TCP transport is enforced to avoid dropped UDP keyframes:
     ```python
     os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
     ```

---

### Issue 4: ByteTrack Fails with `ModuleNotFoundError: No module named 'lap'`
- **Symptom:** ByteTrack tracker crashes during bipartite matching.
- **Root Cause:** The `lap` (Linear Assignment Problem) C++ wheel failed to compile or is missing Microsoft Visual C++ Build Tools on Windows.
- **Solution:**
  1. StorePulse AI includes an internal pure-Python / `scipy.optimize.linear_sum_assignment` fallback in `tracking/tracker.py`.
  2. Ensure the fallback flag is active:
     ```python
     # tracking/tracker.py
     try:
         import lap
     except ImportError:
         from scipy.optimize import linear_sum_assignment
         # Scipy fallback executes without requiring C++ build tools
     ```

---

### Issue 5: `GET /api/zones/transitions` Returns Zero Transitions
- **Symptom:** Frontend transition matrix shows "No transition data recorded yet" (`total_transitions = 0`).
- **Root Cause:** This is **expected honest behavior** when running static camera frames where tracked persons do not move across zone boundaries.
- **Verification:**
  1. Check the response field `data_sufficient`. If `false`, the system correctly indicates insufficient movement observations.
  2. To populate transition records for testing or demonstration, run the transition generator:
     ```powershell
     python scripts/populate_test_transitions.py
     ```
  3. Re-query `/api/zones/transitions`:
     ```json
     {
       "total_transitions_recorded": 7,
       "data_sufficient": true,
       "transitions": [...]
     }
     ```

---

### Issue 6: High CPU Utilization / GPU Out-Of-Memory (OOM)
- **Symptom:** System slows down, fan speed spikes, or CUDA throws `OutOfMemoryError`.
- **Root Cause:** YOLO inference running at full unconstrained camera frame rate (60 FPS) without frame-skipping.
- **Optimization Solution:**
  1. Enable frame skipping in `backend/settings.py`:
     ```python
     FRAME_SKIP = 3  # Process 1 frame every 3 incoming frames (10 FPS effective)
     ```
  2. Use FP16 half-precision inference:
     ```python
     model.to("cuda").half()
     ```
  3. Ensure OpenCV buffers are clamped to 1 frame to prevent memory accumulation:
     ```python
     cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
     ```

---

### Issue 7: WebSocket Reconnection Loops (`WebSocket is closed before connection is established`)
- **Symptom:** Browser console shows repeated red errors: `WebSocket connection to 'ws://localhost:8000/ws' failed`.
- **Root Cause:** Frontend attempting to connect before backend Uvicorn server has finished initializing the YOLO weights.
- **Solution:**
  1. In `dashboard/src/hooks/useStorePulseWS.js`, verify exponential backoff is active:
     ```javascript
     const retryDelay = Math.min(1000 * Math.pow(2, retryCount), 10000);
     setTimeout(connectWebSocket, retryDelay);
     ```
  2. Check CORS and WebSocket host permissions in `backend/main.py`:
     ```python
     app.add_middleware(
         CORSMiddleware,
         allow_origins=["*"],
         allow_credentials=True,
         allow_methods=["*"],
         allow_headers=["*"],
     )
     ```

---

## 3. Logging & Debugging Modes

### 3.1 Enabling Detailed Debug Logs

Set the log level to `DEBUG` via environment variable or `.env`:

```powershell
$env:STOREPULSE_LOG_LEVEL = "DEBUG"
python backend/main.py
```

### 3.2 Key Log Signatures to Watch

| Log Level | Log Message Pattern | Meaning / Action Required |
|:---|:---|:---|
| `INFO` | `[Pipeline] Model YOLO11n loaded successfully on device: cuda:0` | Normal startup. GPU acceleration active. |
| `WARNING` | `[Pipeline] GPU unavailable, falling back to CPU ONNX runtime` | Safe fallback. Frame latency will be ~25ms higher. |
| `WARNING` | `[ZoneAnalytics] Track ID 104 jumped > 200px in 1 frame (possible occlusion)` | Kalman filter will smooth trajectory. |
| `INFO` | `[BottleneckEngine] Zone 'checkout_counter' flagged CRITICAL (dwell: 74s)` | Operational alert triggered. |
| `ERROR` | `[VideoCapture] Frame read failed after 5 retries. Resetting capture stream.` | Camera network glitch; automatic reconnection underway. |

---

## 4. Thread Deadlock Diagnostic Procedure

Because the computer vision pipeline runs asynchronously alongside FastAPI, state synchronization uses `threading.Lock`. If the server ever hangs:

1. **Check Thread Activity:**
   Add this diagnostic snippet to `backend/main.py` under `/debug/threads`:
   ```python
   import threading
   import sys

   @app.get("/debug/threads")
   def dump_thread_stacks():
       code = []
       for threadId, stack in sys._current_frames().items():
           code.append(f"\n# ThreadID: {threadId}")
           for filename, lineno, name, line in traceback.extract_stack(stack):
               code.append(f"File: '{filename}', line {lineno}, in {name}\n  {line.strip()}")
       return "\n".join(code)
   ```
2. **Access Diagnostic Route:**
   Navigate to `http://127.0.0.1:8000/debug/threads` to see exactly which line of code is holding or awaiting a lock.
3. **Lock Timeout Protection:**
   All StorePulse locks utilize timeouts (`lock.acquire(timeout=2.0)`) to ensure that thread deadlocks fail gracefully rather than permanently freezing the backend.
