# StorePulse AI — System Architecture
**Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator  
**Developer / Owner:** Omkar Gurav  
**Architecture Specification**  
**Date:** October 2026  

---

## 1. System Overview

StorePulse AI transforms raw retail camera footage into actionable spatial intelligence and interactive layout optimization. It combines real-time computer vision with an interactive What-If Layout Simulator to help retail store operators analyze current customer flow and simulate spatial rearrangements before physical remodeling.

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

## 2. End-to-End Pipeline Architecture

```
                      Video / RTSP / Webcam
                                │
                                ▼
                     YOLO11 Object Detection
                     (Anchor-free, NMS filtered)
                                │
                                ▼
                        ByteTrack Tracker
                   (Kalman Filter + IoU Associator)
                                │
             ┌──────────────────┼──────────────────┐
             ▼                  ▼                  ▼
     Line Counter       Heatmap Generator    Zone Analytics
    (Virtual Cross)    (2D Accumulator)    (Polygon In/Out)
             │                  │                  │
             │                  │                  ├─ Dwell Timer
             │                  │                  ├─ Transitions
             │                  │                  └─ Congestion Alerts
             │                  │                  │
             └──────────────────┼──────────────────┘
                                │
                                ▼
                   Flow Friction Score Engine
                   (Weighted Multi-factor Model)
                                │
                                ▼
                         FastAPI Server
           ┌────────────────────┴────────────────────┐
           ▼                                         ▼
   WebSocket Broadcast                       REST API Endpoints
   (JSON real-time stream)                   (/api/zones, /api/layouts,
           │                                  /api/analytics, /snapshot)
           │                                         │
           └────────────────────┬────────────────────┘
                                │
                                ▼
                      React 19 + Vite UI
                   (10 Integrated Dashboards)
```

---

## 3. Core Subsystems

### 3.1 Computer Vision Pipeline
- **Detection (`detection/`):** YOLO11 nano (`yolo11n.pt`) detects persons in video frames with confidence thresholding (default 0.4).
- **Tracking (`tracking/tracker.py`):** ByteTrack assigns persistent numeric tracking IDs to each detected person, tracking bottom-center bounding box coordinates across frames.
- **Line Counter (`tracking/counter.py`):** Detects orientation-aware line crossings to count total entries and exits without duplicate increments.
- **Heatmap Generator (`analytics/heatmap.py`):** Accumulates Gaussian kernels onto a 2D float32 array, generating foot-traffic density overlays.

### 3.2 Zone Analytics Engine (`backend/zone_analytics.py`)
- **Polygon Boundary Testing:** Uses the ray-casting algorithm to test whether bottom-center coordinates of each tracked person fall within defined multi-point polygon zones.
- **Dwell Time Tracking:** Records continuous visit start and end times per anonymous tracking ID. Calculates average, median, and maximum dwell times while preventing duplicate entries for continuous presence.
- **Zone-to-Zone Transitions:** Maintains an in-memory transition matrix tracking paths between zones (e.g., `Entrance -> Grocery -> Checkout`).
- **Congestion Alerts:** Compares zone occupancy to configured capacity and triggers alerts when thresholds are exceeded.

### 3.3 Flow Friction Score Engine (`backend/flow_friction.py`)
Summarizes congestion and customer flow friction on an explainable 0–100 scale:
$$\text{Score} = \frac{w_{\text{occ}} \cdot S_{\text{occ}} + w_{\text{dwell}} \cdot S_{\text{dwell}} + w_{\text{queue}} \cdot S_{\text{queue}}}{w_{\text{occ}} + w_{\text{dwell}} + w_{\text{queue}}}$$

- **Occupancy Factor ($S_{\text{occ}}$):** Ratio of current occupancy to configured capacity, saturating at $1.5\times$ capacity.
- **Dwell Factor ($S_{\text{dwell}}$):** Ratio of observed dwell to zone-type baseline, evaluated when sample count $\ge 3$.
- **Queue Factor ($S_{\text{queue}}$):** Ratio of checkout queue length to threshold alert limit.
- **Alert Tiers:** `LOW` ($<40$), `MEDIUM` ($40-64$), `HIGH` ($65-84$), `CRITICAL` ($\ge 85$).

### 3.4 Interactive What-If Simulator (`backend/simulator.py` & `dashboard/src/pages/WhatIfSimulator.jsx`)
- **Floor-Plan Editor:** Interactive canvas allowing store operators to add, drag, resize, rotate, and delete virtual shelves, product displays, checkout counters, and obstacles.
- **Heuristic Simulation Engine:** Evaluates proposed layout alterations by analyzing:
  - Space utilization percentage ($100 - \text{free space}$).
  - Manhattan walking distance from entrance to demand-weighted zones.
  - Route conflict scores derived from obstacle overlap and aisle narrowing.
  - Checkout accessibility distance.
- **Scenario Comparison:** Generates side-by-side comparison tables with absolute differences, percentage changes, directional indicators (`BETTER`, `WORSE`, `SAME`), and transparent heuristic limitations.

### 3.5 Web Application & UI Architecture
- **Framework:** React 19, Vite, React Router v7, Recharts, Lucide React.
- **Pages:**
  1. `Overview` — Executive KPI summary, live camera feed, queue health, zone occupancy.
  2. `Live Analytics` — Real-time frame statistics, active tracking count, queue chart.
  3. `Zone Analytics` — Dwell-time distribution, occupancy bars, congestion levels.
  4. `Movement Flow` — Zone-to-zone transitions, sankey-style route flows.
  5. `Heatmaps` — Real-time traffic density visualizations and export controls.
  6. `Queue Monitoring` — Checkout queue occupancy, trend history, and threshold alerts.
  7. `Flow Friction` — Zone-by-zone friction scores, contributing factors, recommendations.
  8. `What-If Simulator` — Signature interactive floor-plan canvas editor.
  9. `Scenario Comparison` — Baseline vs. proposed comparison matrix.
  10. `Settings & Privacy` — Privacy controls, retention settings, threshold tuning.

---

## 4. Privacy & Data Handling Principles

1. **No Facial Recognition:** Biometric identification and identity persistence are strictly absent.
2. **Short-Lived Ephemeral Tracking:** Tracking IDs are transient integer identifiers stored in memory and purged upon session termination or track expiration.
3. **No Video Retention:** CCTV frames are processed in-memory in real time; raw video footage is never stored to disk.
4. **Aggregate Analytics:** All downstream metrics (dwell times, counts, friction scores) are anonymized aggregate distributions.
