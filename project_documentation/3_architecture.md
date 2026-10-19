# StorePulse AI — End-to-End System Architecture

**Document:** System Architecture Specification  
**Author:** Omkar Gurav  
**Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator  
**Version:** 1.0.0  

---

## 1. System Overview & Architecture Diagram

StorePulse AI connects edge computer vision, real-time spatial analytics, and an interactive digital twin into a unified, responsive architecture:

```mermaid
graph TD
    subgraph "Video Ingestion Layer"
        CCTV["CCTV Video File (.mp4)"] --> StreamHandler
        RTSP["IP Camera (RTSP / HTTP)"] --> StreamHandler
        Webcam["Physical Webcam (Device 0)"] --> StreamHandler
        StreamHandler["Stream Ingest & Reconnect Backoff"]
    end

    subgraph "Computer Vision Pipeline"
        StreamHandler --> FrameRead["Frame Ingest (OpenCV)"]
        FrameRead --> YOLO["YOLO11n Person Detector (PyTorch/CPU)"]
        YOLO --> BoundingBoxes["Bounding Boxes [x1, y1, x2, y2]"]
        BoundingBoxes --> ByteTrack["ByteTrack Association (Kalman + LAP)"]
        ByteTrack --> TrackedPersons["Tracked Persons (ID, Centroid, BBox)"]
    end

    subgraph "Spatial Analytics Subsystem"
        TrackedPersons --> LineCounter["Line Counter (In/Out Occupancy)"]
        TrackedPersons --> HeatmapEngine["Gaussian Heatmap Accumulator (float32)"]
        TrackedPersons --> QueueMonitor["Cashier Queue Monitor"]
        TrackedPersons --> ZoneEngine["Zone Analytics Engine"]
        ZoneEngine --> DwellCalc["Elapsed Timestamp Dwell Engine"]
        ZoneEngine --> Bottlenecks["Explainable Bottleneck Detector"]
        ZoneEngine --> TransMatrix["Zone Transition Probability Matrix"]
    end

    subgraph "Scoring & Simulation Engines"
        DwellCalc --> FlowFriction["Flow Friction Engine (0-100)"]
        QueueMonitor --> FlowFriction
        LineCounter --> FlowFriction
        TransMatrix --> SimulatorEngine["Heuristic Layout Simulator v2"]
        LayoutStore["Layout Store (Baseline & Proposed)"] --> SimulatorEngine
    end

    subgraph "FastAPI Backend & Transport"
        FlowFriction --> FastAPIMain["FastAPI Application"]
        ZoneEngine --> FastAPIMain
        SimulatorEngine --> FastAPIMain
        FastAPIMain --> WSBroadcast["WebSocket Broadcast (/ws)"]
        FastAPIMain --> MJPEGFeed["MJPEG Video Stream (/snapshot)"]
        FastAPIMain --> RESTEndpoints["REST APIs (/api/zones, /api/layouts)"]
    end

    subgraph "Dashboard Frontend (React 19 + Vite)"
        WSBroadcast --> WSClient["useWebSocket Hook"]
        RESTEndpoints --> ReactPages["10 Operations Pages"]
        MJPEGFeed --> ReactPages
        ReactPages --> SimulatorUI["What-If Floor Plan Canvas (SVG)"]
        ReactPages --> ComparisonUI["Scenario Comparison Matrix"]
        ReactPages --> MatrixUI["Transition Matrix Grid"]
    end
```

---

## 2. Subsystem Breakdown

### 2.1 Computer Vision & Tracking Engine
- **Module:** `detection/detector.py`, `tracking/tracker.py`, `tracking/counter.py`
- **Detector:** Ultralytics YOLO11n running on the host CPU with Class 0 (`person`) filtering and a confidence threshold of $0.40$. Input coordinates are clamped defensively to frame boundaries.
- **Tracker:** ByteTrack multi-object tracker using Kalman state propagation and linear assignment (`lap==0.5.13`).
- **Tracking Data Structures:**
  ```python
  class TrackedPerson:
      track_id: int
      bbox: Tuple[int, int, int, int]      # x1, y1, x2, y2
      bottom_center: Tuple[int, int]       # Ground contact point
      confidence: float
  ```
- **Pruning Strategy:** Inactive trajectories are pruned after $2 \times \text{track\_buffer}$ (60 frames) of camera absence to prevent memory leakage.

---

### 2.2 Spatial Analytics & Bottleneck Engine
- **Module:** `backend/zone_analytics.py`, `backend/flow_friction.py`
- **Coordinate Space:** Polygons and bottom-center positions are normalized to $[0.0, 1.0]$.
- **Dwell Calculation:** Computes true elapsed duration $\Delta t = t_{\text{exit}} - t_{\text{enter}}$ based on deterministic frame timestamps ($t$), preventing framerate skew.
- **Hysteresis State Machine:**
  ```
  [Inside Zone] ---> (Crosses Boundary) ---> [Pending Exit (2.0s Grace Window)]
                                                    │                   │
                                          (Re-enters within 2.0s) (Grace Expired)
                                                    │                   │
                                                    ▼                   ▼
                                             [Exit Canceled]     [Visit Finalized]
  ```
- **Bottleneck Persistence Window:** Occupancy spikes must sustain for $\ge 4.0\text{s}$ before triggering alerts. Alerts maintain a $1.5\text{s}$ cooldown before clearing.

---

### 2.3 Heuristic What-If Layout Simulator
- **Module:** `backend/simulator.py`, `backend/routers/layouts.py`
- **Walkable Aisle Clearance ($d_{\text{clearance}}$):**
  $$d_{\text{clearance}}(z) = \min_{e \in \text{Fixtures}} \|\text{Centroid}(z) - \text{BBox}(e)\|$$
- **Bottleneck Risk Index (BRI):**
  $$\text{BRI} = \min(100.0, 0.4 \cdot \text{CongestionRatio} + 0.3 \cdot \text{ConflictScore} + 0.3 \cdot \text{Density})$$
- **Fixture Overlap Collision (AABB):** Evaluates fixture bounding boxes to prevent invalid overlapping geometry.
- **Zero-Baseline Mathematical Safety:** Handles zero-baseline metrics cleanly without division-by-zero crashes.

---

### 2.4 FastAPI Asynchronous Backend & Concurrency
- **Module:** `backend/main.py`, `backend/pipeline.py`
- **Threading Model:**
  - `AnalyticsPipeline` runs in a dedicated background daemon thread (`self.thread`), isolating heavy CPU computer vision from API request processing.
  - Inter-thread data access is synchronized using re-entrant `threading.Lock()` wrappers.
  - FastAPI handles HTTP requests and WebSocket connections on the `asyncio` event loop.
- **WebSocket Broadcast:** A lightweight worker task polls the pipeline runner every 100ms and broadcasts telemetry payloads to all active WebSocket clients.

---

### 2.5 React 19 Frontend Dashboard
- **Module:** `dashboard/src/`
- **Tooling:** React 19, Vite 6, React Router v7, Lucide Icons, Recharts.
- **State & Communication:**
  - `useWebSocket`: Custom React hook maintaining persistent WebSocket connection with automatic reconnect.
  - Local State: Fast React state managing the SVG canvas without heavy external canvas libraries.
- **Production Bundle:** Minified, tree-shaken assets yielding $< 750\text{KB}$ JavaScript bundle and $< 20\text{KB}$ CSS.
