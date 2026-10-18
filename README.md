# StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator

> **Transforming retail camera feeds into actionable customer flow intelligence and interactive spatial layout optimization.**

**Developer & Architect:** Omkar Gurav  
**Project:** StorePulse AI  
**License:** MIT  

---

## 1. Overview & Problem Statement

Physical retail operators frequently make layout modifications—moving shelves, shifting promotional displays, and relocating checkout lanes—without quantitative data on how these changes affect customer movement, dwell times, and bottleneck formation.

**StorePulse AI** bridges this gap by pairing a real-time computer vision pipeline with a **What-If Layout Simulator**:
1. **Observe Reality:** Real-time YOLO11 detection and ByteTrack tracking continuously monitor store entrances, checkout queues, and custom polygon zones, calculating dwell times, transitions, and multi-factor **Flow Friction Scores**.
2. **Simulate Alternatives:** An interactive SVG-based floor-plan editor allows managers to test proposed spatial rearrangements (e.g., widening aisles, moving endcaps, shifting registers) before physical remodeling.
3. **Compare Scenarios:** Quantitative baseline-vs-proposed comparisons estimate differences in walking distance, route conflict risks, and space utilization with clear heuristic assumptions.

---

## 2. Key Features

### 👁️ Computer Vision & Tracking
- **YOLO11 Person Detection:** High-speed anchor-free object detection for individuals in overhead and angled CCTV views.
- **ByteTrack Multi-Object Tracking:** Persistent numeric tracking IDs across frames using Kalman filters and IoU association.
- **Directional Line Counter:** Virtual entrance/exit crossing line tracking store occupancy without double-counting.
- **Foot-Traffic Heatmaps:** 2D Gaussian kernel accumulation revealing high-density customer browsing hotspots.

### 📍 Spatial Analytics & Flow Friction
- **Polygon Store Zone Dwell Analytics:** Ray-casting polygon geometry tracking entries, occupancy, average/median/max dwell times across customizable store zones (Entrance, Checkout, Grocery, Electronics, Promo).
- **Zone-to-Zone Transition Matrix:** Captures paths and flow vectors between departments.
- **Flow Friction Score Engine (0–100):** Multi-factor weighted decision metric combining occupancy ratios, dwell saturation, and queue build-up to highlight congestion.

### 📐 Interactive What-If Layout Simulator (Signature Feature)
- **Interactive Floor Plan Canvas:** Full drag-and-drop, resize, rotate, and delete controls for virtual shelves, checkout counters, and obstacles.
- **Heuristic Layout Simulation Engine:** Calculates walking distance to demand-weighted zones, space utilization percentages, and route conflict risks.
- **Side-by-Side Scenario Comparison:** Direct metric-by-metric delta comparison table between baseline and proposed designs with directional badges (`BETTER`, `WORSE`, `SAME`).

### 🛡️ Privacy by Design
- **No Facial Recognition or Biometric ID:** No identity tracking, facial embeddings, or demographic profiling enabled by default.
- **Ephemeral Tracking:** Track IDs exist purely in temporary RAM and are purged upon exit.
- **Zero Video Retention:** Video frames are processed in-memory in real time; raw video is never persisted.

---

## 3. Architecture & Tech Stack

```
                   CCTV Video / RTSP / Webcam
                               │
                               ▼
                    YOLO11 Person Detection
                               │
                               ▼
                       ByteTrack Tracker
                               │
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
       Line Counter       Heatmap Engine   Zone Analytics
      (Entries/Exits)    (2D Accumulator) (Polygon Dwell)
             │                 │                 │
             └─────────────────┼─────────────────┘
                               │
                               ▼
                   Flow Friction Score Engine
                               │
                               ▼
                    FastAPI Backend (Python)
                     ├── WebSocket  (/ws)
                     ├── MJPEG Feed (/snapshot)
                     └── REST APIs  (/api/zones, /api/layouts, /api/analytics)
                               │
                               ▼
                  React 19 Dashboard (Vite)
                     ├── 10 Operational Views
                     ├── Interactive SVG Simulator
                     └── Scenario Comparison Matrix
```

### Tech Stack Details

| Layer | Technologies |
|---|---|
| **Computer Vision** | YOLO11 (Ultralytics), ByteTrack, OpenCV |
| **Backend & APIs** | Python 3.10–3.14, FastAPI, Uvicorn, WebSockets, Pydantic |
| **Frontend UI** | React 19, Vite 6, React Router v7, Recharts, Lucide Icons |
| **Testing & Quality**| Pytest, Starlette TestClient, ESLint |

---

## 4. Getting Started

### Prerequisites
- **Python:** 3.10 to 3.14 installed
- **Node.js:** v18+ and `npm` installed
- **Git**

### Installation

#### 1. Clone the repository
```bash
git clone https://github.com/omkargurav/storepulse-ai.git
cd storepulse-ai
```

#### 2. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*Windows Powershell:*
```powershell
Copy-Item .env.example .env
```

#### 3. Python Backend Setup
```bash
# Install backend dependencies
pip install -r backend/requirements.txt
```

#### 4. Frontend Dashboard Setup
```bash
cd dashboard
npm install
cd ..
```

---

## 5. Running the Application

### Step 1: Start the FastAPI Backend
```bash
python backend/main.py
```
- API server runs at: `http://localhost:8000`
- Interactive API Docs (Swagger): `http://localhost:8000/docs`
- MJPEG Live Video Stream: `http://localhost:8000/snapshot`
- Real-time WebSocket: `ws://localhost:8000/ws`

*(Note: If no physical camera or video file is present, the backend automatically runs in safe demo mode with synthetic simulation data clearly labeled.)*

### Step 2: Start the React Dashboard
In a second terminal:
```bash
cd dashboard
npm run dev
```
- Open browser at: `http://localhost:5173`

---

## 6. How to Use the What-If Simulator

1. Navigate to **What-If Simulator** (`/simulator`) in the dashboard sidebar.
2. The current **Baseline Layout** is loaded automatically on the SVG canvas.
3. **Add Elements:** Click **+ Shelf**, **+ Display**, **+ Checkout**, or **+ Obstacle** in the top toolbar to insert store fixtures.
4. **Edit Layout:** Click any element to select it; drag to reposition, use handle controls to resize, or adjust dimensions and rotation in the property inspector panel.
5. **Save Layout:** Click **Save Proposed** to persist the new layout with a descriptive name.
6. **Compare Scenarios:** Navigate to **Scenario Comparison** (`/comparison`) to review walking distance changes, space utilization deltas, and route conflict scores.

---

## 7. Testing & Validation

Run the automated test suite covering zone analytics, dwell timers, flow friction formulas, layout CRUD, and API endpoints:

```bash
python -m pytest tests -v
```

**Results:**
- `19 passed in 7.21s (100% pass rate)`
- Production build validation: `npm run build` completed cleanly with Vite in 10.41s.

For detailed test coverage and validation methodology, refer to [`docs/VALIDATION.md`](docs/VALIDATION.md).

---

## 8. Documentation Index

- [Implementation Audit & Changelog](docs/IMPLEMENTATION_AUDIT.md)
- [System Architecture Specification](docs/ARCHITECTURE.md)
- [REST & WebSocket API Reference](docs/API.md)
- [Privacy & Responsible Analytics Policy](docs/PRIVACY.md)
- [Testing & Validation Report](docs/VALIDATION.md)

---

## 9. Known Limitations

- **Camera Perspective:** High-mounted indoor cameras yield the highest tracking accuracy. Ultra-wide outdoor cameras where pedestrians appear under $20\times20$ pixels have reduced detection confidence.
- **Heuristic Layout Engine:** Spatial simulation outputs are mathematical directional approximations based on geometry and customer demand weights, not deterministic guarantees of physical shopper behavior.
- **Speed Calibration:** Physical speed calculation in meters/second requires extrinsic homography plane calibration; uncalibrated setups measure pixel displacement.

---

## 10. Developer & Ownership

**Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator  
**Developer & Architect:** Omkar Gurav  
**License:** MIT  

### Technology Stack & Open-Source Libraries
StorePulse AI utilizes the following open-source frameworks:
- **Ultralytics YOLO11** for computer vision object detection
- **ByteTrack** for multi-object association and tracking
- **OpenCV** for image processing and matrix transformations
- **FastAPI & Uvicorn** for asynchronous ASGI backend and WebSocket broadcast
- **React 19 & Vite** for responsive operations interface
- **Recharts** for real-time data visualization