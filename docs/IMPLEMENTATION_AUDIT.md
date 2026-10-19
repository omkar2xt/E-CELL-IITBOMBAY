# StorePulse AI — Implementation Audit
**Auditor / Developer:** Omkar Gurav
**Date:** October 2026
**Target Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator

---

## 1. Repository Structure

```
storepulse-ai/
├── detection/        YOLO11 person detection (standalone module)
├── tracking/         ByteTrack multi-person tracking + line counter
├── analytics/        Heatmap, queue monitor, demographic estimation
├── backend/          FastAPI server (WebSocket + MJPEG)
└── dashboard/        React + Vite + Recharts frontend
```

## 2. Feature Audit

### 2.1 Working Features (Verified via Code Inspection)

| Feature | Module | Status |
|---------|--------|--------|
| YOLO11 person detection | detection/ | VERIFIED |
| ByteTrack multi-person tracking | tracking/tracker.py | VERIFIED |
| Virtual line crossing counter (IN/OUT) | tracking/counter.py | VERIFIED |
| Foot-traffic heatmap (Gaussian kernel) | analytics/heatmap.py | VERIFIED |
| Queue zone monitoring with alerts | analytics/queue_monitor.py | VERIFIED |
| Demographics estimation (OpenCV DNN + Caffe) | analytics/demographic.py | VERIFIED |
| FastAPI WebSocket broadcast | backend/main.py | VERIFIED |
| MJPEG stream /snapshot | backend/main.py | VERIFIED |
| Background pipeline thread | backend/pipeline.py | VERIFIED |
| React dashboard (stat cards, queue chart) | dashboard/src/ | VERIFIED |
| WebSocket client hook | dashboard/src/hooks/ | VERIFIED |
| Trajectory storage per track_id | tracking/tracker.py | VERIFIED |

### 2.2 Phase 2 Pipeline Audit Findings & Resolution

| Defect / Risk Identified | Affected File | Resolution / Verification |
|---|---|---|
| Bare `import config` across packages causing namespace collisions | `detection/detector.py`, `tracking/tracker.py`, `tracking/counter.py`, `analytics/heatmap.py`, `analytics/queue_monitor.py` | Fixed with resilient package-aware imports (`from detection import config` with fallback) |
| Inactive track pruning lacked duration threshold | `tracking/tracker.py` | Added `last_seen_frame` tracking; prune trajectories only after $2 \times \text{track\_buffer}$ absence |
| `LineCounter` track state memory growth | `tracking/counter.py` | Implemented `cleanup_old_tracks(active_ids)` to prune terminated track states |
| Video source resolution corrupted RTSP/HTTP URLs | `backend/settings.py` | Preserved streaming protocol prefixes without invalid `os.path.abspath` mangling |
| Infinite busy-spin and missing reconnect on camera disconnect | `backend/pipeline.py` | Implemented bounded exponential backoff reconnection (`CAMERA_RECONNECT_MAX_RETRIES`) and clean EOF rewind |
| Unlabeled synthetic demo mode in telemetry stream | `backend/pipeline.py`, `backend/main.py` | Added explicit `is_demo: False` / `is_demo: True`, `source_type`, and `connection_status` fields |
| Missing `lap` wheel for ByteTrack Hungarian matching | Ultralytics environment | Verified `lap==0.5.13` installation; multi-person ByteTrack operational |

### 2.3 Phase 3 Dwell-Time & Bottleneck Intelligence Audit Findings & Upgrades

| Defect / Risk Identified | Affected File | Resolution / Verification |
|---|---|---|
| Dwell calculation assumed fixed-FPS or relied on frame count increments | `backend/zone_analytics.py` | Migrated to elapsed real timestamps (`t_exit - t_enter`), guarded against negative timestamps (video rewinding) and absurd values. |
| Boundary jitter caused repeated entry/exit event triggering | `backend/zone_analytics.py` | Added boundary hysteresis grace window (`exit_grace_seconds = 2.0s`) via pending exit state machine; cancels candidate exits if person steps back in. |
| Conflated active lingering visitors with completed visit aggregates | `backend/zone_analytics.py` | Separated real-time active metrics (`active_avg_dwell_seconds`, `active_max_dwell_seconds`, `current_occupancy`) from completed aggregates (`avg_dwell_seconds`, `median_dwell_seconds`, `p90_dwell_seconds`, `total_completed_visits`). |
| Missing detection / occlusion permanently orphaned active visits | `backend/zone_analytics.py` | Added track expiration watchdog (`track_expire_seconds = 5.0s`); finalizes incomplete visits with `interrupted = True` and last seen timestamp. |
| Bottleneck alerts flickered during brief 1–2 frame spikes | `backend/zone_analytics.py` | Implemented persistence window (`bottleneck_persistence_seconds = 4.0s`) and cooldown hysteresis; requires sustained congestion before escalating severity. |
| Bottleneck alerts lacked explainability and actionable output | `backend/zone_analytics.py`, `backend/routers/zones.py` | Returns transparent evidence array (occupancy ratios, threshold overages, duration) and operational recommendations (staff deployment, queue balancing). |
| Flow Friction was disconnected from active dwell when completed samples < 3 | `backend/flow_friction.py` | Incorporated real-time active dwell into friction calculation for early-warning responsiveness before visits finalize. |

### 2.4 Phase 4 Intelligent What-If Layout Simulator Audit Findings & Upgrades

| Defect / Risk Identified | Affected File | Resolution / Verification |
|---|---|---|
| Unzoned corridors dropped origin zone during intermediate travel | `backend/zone_analytics.py` | Preserved last-known primary zone across unzoned hallways; transitions record true origin-to-destination paths. |
| Transition counts lacked normalized conditional probabilities | `backend/zone_analytics.py`, `MovementFlow.jsx` | Implemented $P(\text{dest} \mid \text{origin}) = \frac{N_{ij}}{\sum_k N_{ik}}$, matrix grid representation, outflow sums, and data-sufficiency indicators ($N \ge 5$). |
| Simulator used hardcoded weights regardless of empirical movement | `backend/simulator.py` | Connected empirical transition probabilities to demand weighting when sample size $\ge 5$; explicit fallback with documented assumptions. |
| Overlapping fixtures physically obstructed aisles without geometric collision warnings | `backend/simulator.py`, `backend/routers/layouts.py`, `WhatIfSimulator.jsx` | Added `validate_layout()` checking AABB fixture collisions, boundary compliance, and real-time SVG collision warning banners. |
| Zero-baseline metrics caused division-by-zero crashes in scenario comparison | `backend/simulator.py` | Implemented zero-baseline guard: outputs `"N/A (baseline is 0)"` or `"0.0%"` while correctly labeling direction (`WORSE` / `BETTER`). |
| Missing zone-level bottleneck and dwell predictions in scenario comparisons | `backend/simulator.py`, `ScenarioComparison.jsx` | Implemented `zone_comparisons` predicting zone-by-zone aisle clearance, congestion risk (`LOW`/`MEDIUM`/`HIGH`/`CRITICAL`), and localized dwell impact. |
| Simulator lacked undo, rotation, and reset capabilities in frontend | `dashboard/src/pages/WhatIfSimulator.jsx` | Added bounded undo stack, 90° rotation, "Reset to Baseline", "Validate Geometry", and direct "Simulate & Compare" actions. |
| Ambiguity between empirical observations and heuristic predictions | `backend/simulator.py`, `ScenarioComparison.jsx`, `MovementFlow.jsx` | Enforced strict labeling: `[MEASURED REAL OBSERVED EVENTS]` vs. `[HEURISTIC ESTIMATE]`. |

## 3. Architecture & Modular Breakdown

- **Core Vision Pipeline:** `detection/`, `tracking/`, `analytics/`
- **Backend Services:** `backend/main.py`, `backend/pipeline.py`, `backend/settings.py`, `backend/routers/`, `backend/zone_analytics.py`, `backend/flow_friction.py`, `backend/simulator.py`
- **Dashboard Application:** `dashboard/src/` (10 operations pages and components including `WhatIfSimulator.jsx`, `ScenarioComparison.jsx`, `MovementFlow.jsx`)
- **Quality Assurance:** `tests/` automated test suite (46 tests passing with 100% success rate)
- **Workflow Verification:** `scripts/verify_phase4_workflow.py` (8-step E2E execution recorded in `docs/workflow_execution_transcript.json`)
- **Documentation:** `docs/` technical specifications

---

## 4. Phase Implementation Checklist & Status

| Phase | Description | Status | Verification |
|---|---|---|---|
| **Phase 1** | Audit the existing repository & bugs | **DONE** | Documented in `docs/IMPLEMENTATION_AUDIT.md` |
| **Phase 2** | Computer Vision Pipeline Integration | **DONE** | YOLO11n + ByteTrack + Heatmap + LineCounter verified with 10 integration tests |
| **Phase 3** | Dwell-Time & Bottleneck Intelligence | **DONE** | Elapsed timestamp dwell, boundary hysteresis, persistence window, explainable alerts |
| **Phase 4** | Intelligent What-If Layout Simulator | **DONE** | Transition matrix probabilities, heuristic layout simulation, geometry validation, 8-step E2E workflow, 46 passing tests |
| **Phase 5** | Flow Friction Score Engine | **DONE** | Explainable 0-100 formula with component weights in `backend/flow_friction.py` |
| **Phase 6** | Interactive Floor Plan Layout Editor | **DONE** | SVG canvas editor with drag, rotate, resize, delete, undo, and collision warnings |
| **Phase 7** | Scenario Comparison & Bottleneck Changes | **DONE** | Automated metric diffs, zero-baseline safety, zone risk cards, empirical data badges |
| **Phase 8** | Backend REST & WebSocket APIs | **DONE** | Modular routers in `backend/routers/` (`zones.py`, `layouts.py`, `analytics.py`) |
| **Phase 9** | Operations Dashboard & Visualizations | **DONE** | React 19 + Vite responsive dashboard built with 0 errors |
| **Phase 10**| Privacy by Design & Responsible AI | **DONE** | Ephemeral tracking, zero facial ID, documented in `docs/PRIVACY.md` |
| **Phase 11**| Automated Testing & Validation | **DONE** | 46 automated tests passing with 100% success rate |
| **Phase 12**| Documentation & Delivery | **DONE** | Full architectural specs, API reference, validation logs, setup guide |


