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

### 📍 Spatial Analytics & Bottleneck Intelligence
- **Elapsed Timestamp Dwell Analytics & Boundary Hysteresis:** Ray-casting polygon geometry calculating live in-progress and completed dwell statistics (`avg`, `median`, `max`, `p90`), with a 2.0-second boundary hysteresis grace window that prevents duplicate entries.
- **Explainable Bottleneck Detection:** Multi-signal congestion engine monitoring occupancy-to-capacity ratios and lingering thresholds across a 4.0-second persistence window, providing actionable staff recommendations and evidence breakdowns.
- **Zone-to-Zone Transition Matrix:** Captures anonymous customer routing and transfer flow vectors between departments.
- **Flow Friction Score Engine (0–100):** Mathematically bounded composite score evaluating spatial drag from occupancy, active/completed dwell saturation, and queue build-up.

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

## 6. How to Configure Video Input & Store Zones

### 6.1 Configuring Video Input
StorePulse AI supports 3 input modalities configured via `.env` or `backend/settings.py`:
- **Recorded CCTV File:** Set `VIDEO_SOURCE=detection/vid/retail-cctv-footage.mp4` (or any `.mp4`/`.avi` path). Clean EOF looping is handled automatically.
- **Physical Webcam:** Set `VIDEO_SOURCE=0` (or integer index `1`, `2`).
- **RTSP/HTTP IP Camera:** Set `VIDEO_SOURCE=rtsp://admin:pass@192.168.1.50:554/stream1`. Bounded exponential backoff handles network dropouts.
- **Safe Fallback Demo Mode:** If the specified source is missing or offline, the backend automatically runs in safe demo mode with synthetic simulation data, explicitly labeled as `is_demo: True`.

### 6.2 Configuring Store Zones
Zones are defined as normalized 2D polygons ($x, y \in [0.0, 1.0]$) relative to the camera field of view:
- **Default Zones:** The system initializes with 5 standardized retail zones: `Entrance`, `Checkout`, `Grocery / Aisles`, `Electronics`, and `Promo Display`.
- **REST API:**
  - Create/Update: `POST /api/zones/` or `PUT /api/zones/{zone_id}` with polygon points, capacity, and dwell alert thresholds.
  - Delete: `DELETE /api/zones/{zone_id}`.
  - Query Stats: `GET /api/zones/stats` or `GET /api/zones/bottlenecks`.

---

## 7. How Dwell Time & Bottlenecks are Calculated

### 7.1 Elapsed Timestamp Dwell-Time Engine
- **Formula:** $\Delta t = t_{\text{exit}} - t_{\text{enter}}$ using frame timestamps ($t$), completely independent of video framerate fluctuations or hardware throttling.
- **Boundary Hysteresis Grace Period (2.0s):** When a tracked individual crosses a polygon edge, an exit candidate is placed into a pending buffer for $2.0\text{s}$. If the person steps back into the zone within this window, the exit is canceled—eliminating boundary jitter and false duplicate counts.
- **Track Expiration Watchdog (5.0s):** If a person is lost due to occlusion or camera blindspots for $>5.0\text{s}$, the visit is finalized with `interrupted = True` at the last verified detection.
- **Active vs. Completed Separation:**
  - **Active In-Progress:** `active_avg_dwell_seconds`, `active_max_dwell_seconds`, `current_occupancy`.
  - **Completed Visits:** `avg_dwell_seconds`, `median_dwell_seconds`, `max_dwell_seconds`, `p90_dwell_seconds`.

### 7.2 Multi-Signal Explainable Bottleneck Detection
Monitors 3 concurrent operational signals:
1. **Occupancy Ratio:** $\frac{\text{Current Occupancy}}{\text{Configured Capacity}}$ (Warning $\ge 1.0\times$, Severe $\ge 1.2\times$, Critical $\ge 1.5\times$).
2. **Lingering Count:** Number of active visitors exceeding `dwell_alert_seconds`.
3. **Persistence Window (4.0s):** Transient 1–2 frame spikes do NOT trigger an alert. Only sustained congestion over $\ge 4.0\text{s}$ escalates severity.
- **Actionable Outputs:** Alerts provide severity (`LOW`/`MEDIUM`/`HIGH`/`CRITICAL`), audited evidence strings, and contextual operational staff recommendations.

### 7.3 Composite Flow Friction Score (0–100)
$$\text{Score} = \min\left(100.0, \frac{0.40 \cdot S_{\text{occ}} + 0.40 \cdot S_{\text{dwell}} + 0.20 \cdot S_{\text{queue}}}{1.0}\right)$$
Incorporates active dwell early-warning when completed sample size is small ($N < 3$).

---

## 8. How the What-If Simulator Works

### 8.1 Interactive Floor Plan Editor (`/simulator`)
1. Navigate to **What-If Simulator** (`/simulator`) in the dashboard sidebar.
2. The current **Baseline Layout** is loaded automatically into the interactive SVG canvas ($800\times500\text{px}$).
3. **Add Elements:** Toggle to **Add** mode and choose **Shelf**, **Display**, **Checkout**, **Entrance**, **Exit**, or **Obstacle**. Click anywhere on the grid canvas to insert.
4. **Edit & Move:** Select any fixture to drag or resize with snapping ($40\text{px}$ grid).
5. **Rotate & Clone:** Rotate fixtures by $90^\circ$, clone elements, or delete selected items with one click.
6. **Undo Stack:** Use the **Undo** button to revert any accidental modifications.
7. **Collision & Overlap Warnings:** The editor continuously checks axis-aligned bounding boxes (AABB). If two fixtures collide or block an aisle, a red dashed collision indicator and alert banner immediately warn: *"Aisle Collision Warning: N overlapping pairs detected"*.
8. **Validate Geometry:** Click **Validate Geometry** to verify boundaries, dimension sanity, and physical clearances via `/api/layouts/validate`.
9. **Simulate & Compare:** Click **Simulate & Compare** to automatically save the proposed design and launch the comparison report.

### 8.2 Zone Transition Matrix & Movement Flow (`/movement`)
- **Transition Probabilities:** Displays the real observed $P(\text{dest} \mid \text{origin}) = \frac{N_{ij}}{\sum_k N_{ik}}$ matrix grid alongside route breakdown counts.
- **Data Sufficiency Guard:** Requires $N \ge 5$ observed transitions for statistical reliability. If data is insufficient, an explicit warning badge is displayed and heuristic demand priors are used as a fallback.
- **Strict Data Labeling:** Raw live events are explicitly marked `[MEASURED REAL OBSERVED EVENTS]`.

### 8.3 Baseline vs. Proposed Scenario Comparison (`/comparison`)
- **Empirical Routing Indicator:** Displays whether empirical live transition probabilities or category demand priors were used in the simulation.
- **Bottleneck Risk & Walkability:** Compares Space Utilization, Free Walking Space, Centroid Manhattan Walking Distance, and the 0–100 **Bottleneck Risk Index (BRI)**.
- **Zone-by-Zone Congestion Cards:** Evaluates predicted walkable aisle clearance ($d_{\text{clearance}}$), congestion risk tier (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and expected localized dwell impact.
- **Zero-Baseline Mathematical Safety:** Prevents division-by-zero crashes when baseline metric is 0, displaying `"N/A (baseline is 0)"` or `"0.0%"` while correctly assigning the direction flag (`BETTER`, `WORSE`, `SAME`).

---

## 9. Hackathon Demonstration Checklist (For Judges)

Follow this 5-minute walkthrough to verify all core capabilities:

1. **Verify Live Stream & Tracking:**
   - Open `/live`. Observe real-time YOLO11n + ByteTrack tracking with bounding boxes, tracking IDs, and directional count.
2. **Inspect Dwell & Bottleneck Intelligence:**
   - Open `/zones`. Observe live active linger times, completed visit statistics, and explainable bottleneck alert cards.
3. **Inspect Flow Friction Score:**
   - Open `/friction`. Observe the store-level 0–100 score and zone-by-zone friction component breakdowns.
4. **Inspect Observed Transition Matrix:**
   - Open `/movement`. Inspect the observed transition probability matrix grid and data-sufficiency indicators.
5. **Interactive What-If Floor Plan Simulation:**
   - Open `/simulator`.
   - Select **Shelf B** and drag it to collide with **Shelf C**. Notice the immediate red dashed overlap indicator and collision warning banner.
   - Click **Undo** to restore. Move Shelf B toward the center to create a wider clearance aisle.
   - Click **Validate Geometry** $\to$ observe `valid: true`.
   - Click **Simulate & Compare** $\to$ automatically navigates to `/comparison`.
   - Review the Baseline vs Proposed comparison table, Bottleneck Risk Index, and zone clearance cards.

---

## 10. Testing & Validation

Run the automated test suite covering zone analytics, dwell timers, transition probabilities, flow friction formulas, geometry validation, and scenario comparison:

```bash
python -m pytest tests -v
```

**Results:**
- **46 tests passed in 12.79s (100% pass rate)**
- Production build validation: `npm run build` completed cleanly with Vite in 10.67s.
- End-to-End Workflow verification: 8-step workflow executed by `scripts/verify_phase4_workflow.py` and saved to `docs/workflow_execution_transcript.json`.

For detailed test coverage and validation methodology, refer to [`docs/VALIDATION.md`](docs/VALIDATION.md).

---

## 11. Privacy Safeguards & Responsible AI

StorePulse AI was designed specifically to comply with the strictest retail computer vision privacy standards:
1. **Zero Biometrics & Facial Recognition:** The pipeline processes full-body bounding boxes only; facial recognition, face embeddings, and demographic profiling are strictly disabled by default.
2. **Ephemeral Numeric Identifiers:** ByteTrack assigns temporary integer tracking IDs (e.g., `Track 1`, `Track 2`) stored only in volatile memory and purged upon store exit.
3. **Zero Raw Video Storage:** Frames are analyzed in-memory and discarded. Raw customer footage is never written to disk or transmitted to third-party APIs.
4. **Aggregate Spatial Telemetry:** Dwell times, bottleneck counts, and transition probabilities are aggregated at the zone level, making individual journey reconstruction impossible from saved metrics.

---

## 12. Known Assumptions & Limitations

1. **Heuristic Layout Engine:** Spatial simulation outputs are mathematical directional approximations based on geometry and customer demand weights, not deterministic guarantees of physical shopper behavior.
2. **Camera Perspective:** High-mounted indoor cameras yield the highest tracking accuracy. Angled views require polygon calibration per physical lens position.
3. **Speed Calibration:** Physical speed calculation in meters/second requires extrinsic homography plane calibration; uncalibrated setups measure pixel displacement.
4. **Data Sufficiency Rule:** Zone transition routing probabilities require at least 5 observed customer transitions before being applied to layout simulations.

---

## 13. Documentation Index

- [Implementation Audit & Changelog](docs/IMPLEMENTATION_AUDIT.md)
- [System Architecture Specification](docs/ARCHITECTURE.md)
- [REST & WebSocket API Reference](docs/API.md)
- [Privacy & Responsible Analytics Policy](docs/PRIVACY.md)
- [Testing & Validation Report](docs/VALIDATION.md)
- [End-to-End Workflow Transcript](docs/workflow_execution_transcript.json)

---

## 14. Deployment & Scalability
StorePulse AI is a software-only solution, temporarily deployed using Docker and Kubernetes to support consistent application packaging, deployment, and scalability. It combines a React-based dashboard, a FastAPI backend, and a computer vision pipeline to deliver retail analytics without requiring specialized additional hardware. The deployment architecture is designed to support future improvements, cloud integration, and expansion to multiple retail locations.

---
## 15. Developer & Ownership

**Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator  
**Developer & Architect:** Omkar Gurav  
**Challenge:** Everseen Computer Vision AI Hackathon  
**Problem Statement 3:** Dwell-Time & Bottleneck Mapper  
**License:** MIT  

