# StorePulse AI — System Architecture Specification

**Product:** StorePulse AI  
**Description:** Intelligent Retail Flow & What-If Layout Simulator  
**Developer:** Omkar Gurav  
**Architecture Specification:** Phase 1 Foundation & Discovered Architecture  
**Date:** October 2026  

---

## 1. System Overview

StorePulse AI is an edge-and-cloud retail spatial intelligence platform designed to convert physical retail camera feeds into high-resolution operational insights and interactive floor-plan optimizations. The system combines real-time computer vision (YOLO11 + ByteTrack) with spatial zone analytics, flow friction calculations, and an interactive What-If Layout Simulator.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              StorePulse AI                                  │
├──────────────────────────┬─────────────────────────┬────────────────────────┤
│     Computer Vision      │    Spatial Analytics    │  Simulator & Dashboard │
│ • YOLO11 Person Detection│ • Polygon Zone Dwell    │ • Interactive Layout   │
│ • ByteTrack Persistence  │ • Transition Matrix     │   Canvas Editor        │
│ • Line Crossing Counter  │ • Flow Friction Engine  │ • Heuristic Sim Engine │
│ • 2D Gaussian Heatmap    │ • Queue Density Alerts  │ • 10-Page Operations UI│
└──────────────────────────┴─────────────────────────┴────────────────────────┘
```

---

## 2. End-to-End Data Flow

The core data pipeline follows an asynchronous, feed-forward streaming architecture:

```
Video Input (Webcam / CCTV RTSP / Synthetic Generator)
                         │
                         ▼
Person Detection (YOLO11 Nano, Anchor-Free Object Detector)
                         │
                         ▼
Tracking (ByteTrack: Kalman Filter + IoU Associator)
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
   Line Counter    Heatmap Engine  Spatial Zones
  (Virtual Plane) (2D Accumulator)(Polygon Dwell)
         │               │               │
         └───────────────┼───────────────┘
                         │
                         ▼
             Flow Friction Score Engine
            (Weighted Multi-Factor Model)
                         │
                         ▼
         Backend API (FastAPI Asynchronous Core)
           ├── WebSocket Server (/ws @ 10 Hz)
           ├── MJPEG Video Stream (/snapshot)
           └── REST Endpoints (/api/zones, /api/layouts, /api/analytics)
                         │
                         ▼
         Dashboard UI (React 19 + Vite Operations Console)
           ├── 10 Dedicated Operational Dashboards
           ├── Real-Time Recharts Visualizations
           └── SVG What-If Layout Simulator Canvas
```

### Detailed Pipeline Stages

1. **Video Input:** Receives video streams via OpenCV `VideoCapture` (RTSP stream, MP4 recording, or USB webcam). When no hardware feed or video file is available, the system activates a synthetic trajectory generator ensuring zero-downtime demonstration.
2. **Person Detection:** Bounding boxes and confidence scores are generated using `ultralytics.YOLO("yolo11n.pt")`. Detection is strictly restricted to COCO class 0 (`person`) with an empirical confidence threshold of $0.40$.
3. **Tracking:** Unassociated detections are ingested by `ByteTrack`, maintaining identity continuity across camera jitter and brief occlusions using motion prediction (Kalman filters) and spatial overlap (IoU). Each track maintains a history of bottom-center coordinates $(x, y)$.
4. **Analytics Aggregation:**
   - **Line Counter:** Evaluates crossing vectors against horizontal/vertical thresholds to record entries and exits.
   - **Heatmap Generator:** Accumulates 2D Gaussian kernels $(\sigma = 25\text{px})$ onto a normalized float32 matrix.
   - **Spatial Zones:** Evaluates bottom-center coordinates against polygon vertices using Jordan curve ray-casting.
5. **Flow Friction Engine:** Computes an explainable 0–100 congestion metric combining occupancy ratios, dwell saturation, and queue build-up.
6. **Backend API:** An asynchronous FastAPI server orchestrates background pipeline threads, provides RESTful layout CRUD, and broadcasts JSON states over WebSockets to connected clients.
7. **Dashboard UI:** A responsive React 19 single-page application renders live metrics, charts, queue alerts, and provides a drag-and-drop floor plan canvas.

---

## 3. Discovered vs. Planned Components

To ensure engineering transparency, the system architecture distinguishes existing, functioning components from planned extension points:

| Subsystem | Component | Status | Implementation Details |
|---|---|---|---|
| **Vision** | YOLO11 Person Detection | **Existing** | Implemented in `detection/detector.py` using `yolo11n.pt`. |
| **Vision** | ByteTrack Tracking | **Existing** | Implemented in `tracking/tracker.py` with trajectory histories. |
| **Vision** | Virtual Line Counter | **Existing** | Implemented in `tracking/counter.py` for entry/exit tracking. |
| **Vision** | 2D Gaussian Heatmap | **Existing** | Implemented in `analytics/heatmap.py` with Jet/Inferno colormaps. |
| **Vision** | Checkout Queue Monitor | **Existing** | Implemented in `analytics/queue_monitor.py` for cashier polygons. |
| **Vision** | Multi-Camera Calibration & Stitching | **Planned** | Homography ground-plane mapping and camera hand-off across viewpoints. |
| **Spatial** | Polygon Ray-Casting Engine | **Existing** | Implemented in `backend/zone_analytics.py` (in-memory polygon test). |
| **Spatial** | Dwell Duration Statistics | **Existing** | Implemented in `backend/zone_analytics.py` (avg, median, max dwell). |
| **Spatial** | Transition Flow Matrix | **Existing** | Implemented in `backend/zone_analytics.py` (inter-zone transitions). |
| **Spatial** | Zone Congestion Thresholds | **Existing** | Implemented in `backend/zone_analytics.py` (capacity alerts). |
| **Spatial** | Real-Time On-Video Polygon Pen Tool | **Planned** | Interactive visual drawing of polygon zones over the live video canvas in UI. |
| **Flow** | Flow Friction Score (0–100) | **Existing** | Implemented in `backend/flow_friction.py` with multi-factor weights. |
| **Flow** | Historical Trend & ML Forecasting | **Planned** | Time-series forecasting predicting bottlenecks 15–30 minutes in advance. |
| **Simulator** | In-Memory Layout Store | **Existing** | Implemented in `backend/simulator.py` (baseline + proposed CRUD). |
| **Simulator** | Spatial Heuristic Engine | **Existing** | Implemented in `backend/simulator.py` (space utilization & walking distance). |
| **Simulator** | Direct Scenario Comparison Matrix | **Existing** | Implemented in `dashboard/src/pages/ScenarioComparison.jsx`. |
| **Simulator** | A* Path-Finding & Collision Routing | **Planned** | Upgrading Manhattan distance to discrete grid A* path routing around obstacles. |
| **Simulator** | Multi-Floor & Multi-Department Editor | **Planned** | Hierarchical store layouts across multi-level retail department stores. |
| **Backend** | WebSocket Real-Time Stream | **Existing** | Implemented in `backend/main.py` & `backend/ws_manager.py` (10 Hz). |
| **Backend** | REST API Endpoints | **Existing** | Implemented in `backend/routers/` (`zones.py`, `layouts.py`, `analytics.py`). |
| **Backend** | Persistent Database Storage | **Planned** | Migration from in-memory stores to PostgreSQL / SQLite persistent database. |
| **Frontend** | 10 Responsive Dashboards | **Existing** | Implemented in `dashboard/src/pages/` with React 19 & Recharts. |

---

## 4. Planned Architectural Extension Points

### 4.1 Extension Point 1: Zone-Wise Dwell Time & Spatial Geometry
- **Current Foundation:** `backend/zone_analytics.py` uses Jordan curve theorem (ray-casting) against 2D normalized polygons.
- **Extension Hook:**
  - Support dynamic zone resizing via REST endpoint `PUT /api/zones/{zone_id}`.
  - Implement time-decay filtering: historical dwell records decay exponentially ($\lambda = 0.05/\text{min}$) to reflect current conditions rather than lifetime averages.
  - Integrate product category classification (e.g., Grocery vs. Apparel vs. Checkout) with domain-specific dwell expectation thresholds.

### 4.2 Extension Point 2: Movement Analysis & Customer Flow
- **Current Foundation:** Tracks continuous $(x, y)$ trajectories per track ID and records first-order Markov transitions (`Zone A -> Zone B`).
- **Extension Hook:**
  - Upgrade transition matrix to $n$-step path sequencing (`Entrance -> Promo -> Grocery -> Checkout`) to reveal complete shopping journeys.
  - Directional vector accumulation: compute directional velocity vectors $\vec{v} = (\Delta x / \Delta t, \Delta y / \Delta t)$ to identify counter-flow friction and bottlenecks in narrow aisles.

### 4.3 Extension Point 3: Flow Friction Score Engine
- **Current Foundation:** Calculates 0–100 score per zone and store-wide:
  $$\text{Score} = \frac{w_{\text{occ}} \cdot S_{\text{occ}} + w_{\text{dwell}} \cdot S_{\text{dwell}} + w_{\text{queue}} \cdot S_{\text{queue}}}{w_{\text{occ}} + w_{\text{dwell}} + w_{\text{queue}}}$$
- **Extension Hook:**
  - Machine-learned adaptive weight tuning based on historical checkout delays.
  - Predictive friction alerts: trigger proactive staff notifications when velocity trends indicate an imminent queue surge before capacity is breached.

### 4.4 Extension Point 4: What-If Layout Simulator
- **Current Foundation:** `backend/simulator.py` and `dashboard/src/pages/WhatIfSimulator.jsx` provide interactive fixture placement and heuristic metric calculation.
- **Extension Hook:**
  - Discrete Grid A\* Path-Finding: Replace Manhattan distance with obstacle-aware path calculation navigating around placed shelves and display units.
  - Revenue Density Projection: Incorporate dollar value per square meter to project revenue impacts alongside walking distance variations.
  - File Import/Export: Standardize DXF / GeoJSON floor plan import and export.

---

## 5. Core Subsystems Specification

### 5.1 Computer Vision Pipeline
- **Module:** `detection/detector.py`, `tracking/tracker.py`, `analytics/heatmap.py`
- **Model:** Ultralytics YOLO11 Nano (`yolo11n.pt`).
- **Tracker:** ByteTrack algorithm running at 30 FPS with a 30-frame track survival buffer.
- **Privacy Enforcement:** Downstream analytics consume only integer `track_id` and bottom-center coordinates `(x, y)`; video frames are processed transiently in RAM.

### 5.2 Zone Analytics Engine
- **Module:** `backend/zone_analytics.py`
- **Algorithms:**
  - Ray-Casting algorithm for point-in-polygon containment testing:
    ```python
    def contains_point(self, px: float, py: float) -> bool:
        inside = False
        n = len(self.polygon)
        j = n - 1
        for i in range(n):
            xi, yi = self.polygon[i]
            xj, yj = self.polygon[j]
            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside
    ```
  - Continuous dwell duration tracking with duplicate-entry prevention.

### 5.3 Flow Friction Score Engine
- **Module:** `backend/flow_friction.py`
- **Score Scale:** 0 to 100 with four explainable severity tiers:
  - `LOW` ($< 40$): Smooth flow, ample capacity.
  - `MEDIUM` ($40 - 64$): Moderate traffic, normal dwell.
  - `HIGH` ($65 - 84$): Elevated dwell time, near-capacity congestion.
  - `CRITICAL` ($\ge 85$): Severe bottleneck, capacity exceeded or long queue.

### 5.4 What-If Layout Simulator Engine
- **Module:** `backend/simulator.py`
- **Geometry:** 2D coordinate space $(1000 \times 700\text{px})$.
- **Metrics Calculated:**
  - Space Utilization ($\%$): Total fixture footprint area divided by total floor area.
  - Average Walking Distance ($\text{px}$): Distance from entrance to demand-weighted department centroids.
  - Route Conflict Risk ($0 - 100$): Evaluated based on bounding-box overlap and clearance between fixtures.

### 5.5 Operations Dashboard UI
- **Technology:** React 19, Vite 6, React Router v7, Recharts 2.15, Lucide Icons.
- **Pages (10 Operational Views):**
  1. `Overview`: High-level store health, live camera stream, KPI summary cards.
  2. `Live Analytics`: Real-time detection FPS, active tracking count, queue chart.
  3. `Zone Analytics`: Zone occupancy comparison, dwell distribution bar charts.
  4. `Movement Flow`: Zone-to-zone transition flow matrix and path directions.
  5. `Heatmaps`: High-density browsing hotspots with jet colormap overlays.
  6. `Queue Monitoring`: Cashier line length, wait times, threshold alert triggers.
  7. `Flow Friction`: Explainable 0–100 friction score breakdown and recommendations.
  8. `What-If Simulator`: Signature SVG floor-plan canvas with drag, resize, rotate, and delete.
  9. `Scenario Comparison`: Baseline vs. proposed layout delta comparison matrix.
  10. `Settings & Privacy`: Privacy controls, retention periods, alert thresholds.

---

## 6. Privacy & Data Handling Principles

StorePulse AI implements strict Privacy-by-Design principles:

1. **Zero Biometric Identification:** No facial recognition, facial landmarking, or demographic identification models are active in the default operational pipeline.
2. **Short-Lived Ephemeral Tracking:** Track IDs are randomized integer identifiers held in memory and purged upon track termination.
3. **Zero Raw Video Retention:** Video frames are ingested, analyzed in RAM, and immediately discarded. Raw footage is never written to disk or transmitted across external networks.
4. **Anonymized Aggregations:** Downstream APIs and frontend dashboards receive only aggregate, non-reversible statistics (counts, dwell averages, friction scores).
