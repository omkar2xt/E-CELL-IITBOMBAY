# StorePulse AI — Testing & Validation Report
**Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator  
**Developer / Owner:** Omkar Gurav  
**Date:** October 2026  
**Environment:** Python 3.14.3, PyTorch 2.11.0, OpenCV 4.13.0, FastAPI 0.143.0, Node.js v24.14.0, Vite 6.2.0, React 19.2.5  

---

## 1. Automated Test Suite Results

The automated test suite in `tests/` covers unit and integration tests across core engine components and API endpoints:

```bash
$ python -m pytest tests -v
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
collected 19 items

tests/test_api.py::test_health_endpoint PASSED                           [  5%]
tests/test_api.py::test_analytics_status PASSED                          [ 10%]
tests/test_api.py::test_analytics_zones_and_friction PASSED              [ 15%]
tests/test_api.py::test_zones_crud_api PASSED                            [ 21%]
tests/test_api.py::test_layouts_api_and_simulation PASSED                [ 26%]
tests/test_api.py::test_layout_not_found PASSED                          [ 31%]
tests/test_flow_friction.py::test_friction_score_bounds_and_structure PASSED [ 36%]
tests/test_flow_friction.py::test_friction_high_occupancy_triggers_high_score PASSED [ 42%]
tests/test_flow_friction.py::test_friction_missing_or_empty_data PASSED  [ 47%]
tests/test_flow_friction.py::test_friction_store_level_aggregation PASSED [ 52%]
tests/test_simulator.py::test_layout_store_crud PASSED                   [ 57%]
tests/test_simulator.py::test_baseline_preservation PASSED               [ 63%]
tests/test_simulator.py::test_simulator_heuristic_calculation PASSED     [ 68%]
tests/test_zone_analytics.py::test_zone_point_in_polygon PASSED          [ 73%]
tests/test_zone_analytics.py::test_zone_entry_and_occupancy PASSED       [ 78%]
tests/test_zone_analytics.py::test_continuous_presence_no_duplicate_entry PASSED [ 84%]
tests/test_zone_analytics.py::test_zone_transition_and_exit PASSED       [ 89%]
tests/test_zone_analytics.py::test_dwell_time_calculation PASSED         [ 94%]
tests/test_zone_analytics.py::test_capacity_congestion_alert PASSED      [100%]

============================= 19 passed in 7.21s ==============================
```

---

## 2. Frontend Production Build Validation

Vite production build validated with React 19:

```bash
$ cd dashboard && npm run build
> storepulse-ai@1.0.0 build
> vite build

vite v6.2.0 building for production...
✓ 2224 modules transformed.
dist/index.html                   0.47 kB │ gzip:   0.30 kB
dist/assets/index-DKKwhFdo.css   18.43 kB │ gzip:   4.22 kB
dist/assets/index-BGJOHg85.js   715.07 kB │ gzip: 204.10 kB
✓ built in 10.41s
```

---

## 3. Verified Functional Capabilities

| Capability | Module | Verification Method | Status |
|---|---|---|---|
| Person Detection | YOLO11 | OpenCV stream loop on sample footage | **VERIFIED** |
| Tracking & Counting | ByteTrack + Line Counter | Track ID assignment & crossing detection | **VERIFIED** |
| Polygon Zone Dwell | `backend/zone_analytics.py` | Ray casting, dwell timers, duplicate entry prevention | **VERIFIED** |
| Zone Transitions | `backend/zone_analytics.py` | State transitions between polygon zones | **VERIFIED** |
| Flow Friction Scoring | `backend/flow_friction.py` | Multi-factor weighted score calculation | **VERIFIED** |
| What-If Floor Plan Editor | `WhatIfSimulator.jsx` | Drag/drop/resize/rotate SVG canvas | **VERIFIED** |
| Heuristic Sim Engine | `backend/simulator.py` | Geometric pathing & space analysis | **VERIFIED** |
| Baseline vs. Proposed | `ScenarioComparison.jsx` | Dynamic comparison matrix & delta metrics | **VERIFIED** |
| 10-Page Operations UI | `dashboard/src/` | Full navigation, responsive design, dark theme | **VERIFIED** |

---

## 4. Known Limitations

1. **Camera Scale & Tilt:** Detection accuracy drops when individuals appear smaller than $20 \times 20$ pixels in extreme wide-angle or fish-eye CCTV views. Optimal performance occurs at overhead indoor angles with people occupying $\ge 5\%$ of vertical frame height.
2. **Heuristic Simulation Nature:** The What-If Simulator uses spatial geometry and demand-weight modeling. It produces heuristic directional guidance for layout improvements, not exact behavioral predictions.
3. **Calibration:** Physical speed measurement in meters/second requires extrinsic camera plane homography calibration. Without calibration, pixel distance is reported.
