# StorePulse AI — Project Implementation Walkthrough & Milestones

**Document:** Project Implementation Walkthrough  
**Author:** Omkar Gurav  
**Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator  
**Hackathon:** Everseen Computer Vision AI Hackathon  
**Problem Statement 3:** Dwell-Time & Bottleneck Mapper  
**Version:** 1.0.0  

---

## 1. Development Phases & Roadmap

The implementation of StorePulse AI followed a disciplined, iterative engineering methodology divided into five distinct phases:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Architecture Audit & Pipeline Inspection                     │
│ • Dependency auditing, import path fixes, model weight verification   │
├────────────────────────────────────────────────────────────────────────┤
│ Phase 2: Computer Vision Pipeline Integration                         │
│ • YOLO11n person detection + ByteTrack Hungarian tracking             │
│ • Gaussian foot-traffic heatmap + bidirectional virtual line counter  │
├────────────────────────────────────────────────────────────────────────┤
│ Phase 3: Dwell-Time & Bottleneck Intelligence                         │
│ • Timestamp-based dwell engine + 2.0s boundary hysteresis grace window│
│ • Multi-signal explainable bottleneck detection with persistence window│
│ • 0-100 Flow Friction Score engine                                    │
├────────────────────────────────────────────────────────────────────────┤
│ Phase 4: Intelligent What-If Layout Simulator                         │
│ • Empirical transition matrix normalization P(j | i)                  │
│ • Connected simulator demand weighting & walkable aisle clearance     │
│ • Interactive SVG canvas with AABB fixture collision detection & undo │
│ • Scenario comparison report with zero-baseline division guards       │
├────────────────────────────────────────────────────────────────────────┤
│ Phase 5: Submission Readiness & Evaluation Verification               │
│ • 46 automated regression tests passing with 100% success rate        │
│ • Clean Vite frontend production build                                │
│ • Zero-transition investigation & real retail CCTV validation         │
│ • Exhaustive 15-document enterprise documentation suite               │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase-by-Phase Implementation Details

### Phase 1: Architecture Audit & Defensive Hardening
- **Objective:** Audit the existing repository without destructive rewrites, resolving fragile imports, unbounded memory growth, and protocol handling bugs.
- **Key Milestones:**
  - Resolved cross-package namespace collisions in `detector.py`, `tracker.py`, and `heatmap.py`.
  - Added track lifetime tracking (`last_seen_frame`) in ByteTrack, pruning dead tracks after $2 \times \text{track\_buffer}$ absence.
  - Hardened `settings.py` to prevent invalid local path mangling of RTSP and HTTP stream URLs.

### Phase 2: Computer Vision Pipeline Integration
- **Objective:** Establish reliable 30 FPS video ingestion, person detection, and multi-object tracking.
- **Key Milestones:**
  - Integrated Ultralytics YOLO11n anchor-free detection filtered strictly to COCO Class 0 (`person`) with defensive bounding box clamping.
  - Integrated ByteTrack Kalman filtering with linear sum assignment (`lap==0.5.13`).
  - Added bounded exponential backoff reconnection (`CAMERA_RECONNECT_MAX_RETRIES`) for dropped camera streams.
  - Implemented labeled demo simulation fallback with explicit `is_demo: True` flags.
  - Created 10 integration tests in `tests/test_cv_pipeline.py`.

### Phase 3: Dwell-Time & Bottleneck Intelligence
- **Objective:** Build robust spatial dwell analytics and actionable bottleneck detection.
- **Key Milestones:**
  - Replaced frame-count assumptions with real elapsed timestamps ($\Delta t = t_{\text{exit}} - t_{\text{enter}}$).
  - Developed a 2.0-second boundary hysteresis grace window in `_pending_exits`, eliminating boundary jitter.
  - Built an occlusion watchdog finalizing interrupted visits after $5.0\text{s}$ of camera absence.
  - Implemented multi-signal bottleneck detection evaluating occupancy ratios and lingering counts across a $4.0\text{s}$ persistence window.
  - Formulated the 0–100 bounded composite Flow Friction Score.
  - Added 14 unit tests in `tests/test_zone_analytics.py`.

### Phase 4: Intelligent What-If Layout Simulator
- **Objective:** Connect empirical visitor transitions, spatial dwell metrics, and an interactive floor-plan editor into a coherent predictive workflow.
- **Key Milestones:**
  - Preserved origin zones across unzoned hallways to accurately record department-to-department journeys.
  - Computed normalized transition routing probabilities: $P(j \mid i) = \frac{N_{ij}}{\sum_k N_{ik}}$.
  - Implemented AABB fixture collision detection (`validate_layout`) and real-time SVG collision indicators.
  - Built the `WhatIfSimulator.jsx` editor with a 20-state undo stack, $90^\circ$ rotation, and "Reset to Baseline".
  - Connected empirical transition probabilities into layout simulation demand weights when $N \ge 5$.
  - Added zone-by-zone aisle clearance and congestion risk cards in `ScenarioComparison.jsx`.
  - Enforced zero-baseline division guards (`"N/A (baseline is 0)"`).
  - Added 9 simulator unit tests in `tests/test_simulator.py`.

### Phase 5: Submission Readiness & Evaluation Verification
- **Objective:** Prepare the repository for hackathon submission with rigorous validation and zero blockers.
- **Key Milestones:**
  - Investigated the static 0-transition result: proved transitions generate reliably during active movement ($N=7$ on demo agents; Track 4 tracked across 48 frames on CCTV footage).
  - Verified 100% test pass rate: **46 passed in 12.72s**.
  - Verified clean frontend production build: **Vite build in 10.82s**.
  - Executed and recorded the 8-step end-to-end workflow in `docs/workflow_execution_transcript.json`.
  - Authored comprehensive documentation in `project_documentation/`.

---

## 3. Key Technical Challenges & Solutions

| Challenge | Impact | Technical Solution |
|---|---|---|
| **Boundary Jitter** | Customers standing on zone edges triggered dozens of false entries/exits per minute. | Implemented a 2.0s pending exit buffer state machine that cancels exit if customer re-enters within 2.0s. |
| **Framerate Skew** | Video lag or CPU throttling caused fixed-FPS dwell calculations to drift significantly. | Migrated to frame timestamp deltas ($\Delta t = t_{\text{exit}} - t_{\text{enter}}$) independent of framerate. |
| **Unzoned Corridors** | Walking down a hallway between Entrance and Grocery dropped the origin zone. | Preserved `_last_zone[tid]` across unzoned regions until entering a new primary zone. |
| **Fixture Collisions** | Moving virtual shelves into each other created physically impossible layouts. | Implemented 2D Axis-Aligned Bounding Box (AABB) intersection tests with real-time UI collision warnings. |
| **Division by Zero** | Baseline conflict score of 0 caused `ZeroDivisionError` during scenario percentage comparisons. | Added defensive zero-baseline checks outputting `"N/A (baseline is 0)"` while preserving directionality (`WORSE`). |
