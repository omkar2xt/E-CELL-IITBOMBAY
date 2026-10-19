# StorePulse AI — Feature Development Breakdown & Engineering Details

**Document:** Features Development & Engineering Specifications  
**Author:** Omkar Gurav  
**Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator  
**Version:** 1.0.0  

---

## 1. Feature Catalog Overview

StorePulse AI implements 10 integrated features spanning computer vision, spatial mathematics, and predictive layout modeling:

| Feature ID | Feature Name | Core Code Modules | Key Mathematical / Algorithmic Concept |
|---|---|---|---|
| **F-01** | YOLO11n Person Detection | `detection/detector.py` | Anchor-free detection, COCO Class 0, BBox clamping |
| **F-02** | ByteTrack Multi-Person Tracking | `tracking/tracker.py` | Two-stage Hungarian matching, Kalman filter, LAP |
| **F-03** | Virtual Line Crossing Counter | `tracking/counter.py` | Sign-of-cross-product hysteresis, 5px dead-zone |
| **F-04** | Gaussian Foot-Traffic Heatmap | `analytics/heatmap.py` | 2D Gaussian kernel accumulation, JET colormap blending |
| **F-05** | Cashier Queue Monitor | `analytics/queue_monitor.py` | Polygon point-in-polygon containment, threshold alerts |
| **F-06** | Zone Dwell-Time Engine | `backend/zone_analytics.py` | Timestamp deltas ($\Delta t$), 2.0s boundary hysteresis grace |
| **F-07** | Explainable Bottleneck Mapper | `backend/zone_analytics.py` | Multi-factor congestion, 4.0s persistence window |
| **F-08** | Flow Friction Score Engine | `backend/flow_friction.py` | 0–100 bounded composite spatial resistance index |
| **F-09** | Zone Transition Probability Matrix | `backend/zone_analytics.py` | Conditional probability $P(j \mid i)$, unzoned hallway retention |
| **F-10** | What-If Layout Simulator & Comparison | `backend/simulator.py`, `WhatIfSimulator.jsx` | AABB collision detection, $d_{\text{clearance}}$, BRI, zero-baseline safety |

---

## 2. In-Depth Engineering Specifications

### F-01: YOLO11n Person Detection
- **Model:** Ultralytics YOLO11n (~5.4 MB checkpoint).
- **Execution:** CPU inference running at ~113 ms per 1708x959 frame.
- **Defensive Safeguards:**
  - Strict filtering: `cls == 0` (`person`).
  - Coordinate normalization & boundary clamping:
    $$x_1 = \max(0, \min(W, x_1)), \quad y_1 = \max(0, \min(H, y_1))$$
  - Safe zero-detection handling: returns empty list if no persons detected without exception.

---

### F-02: ByteTrack Multi-Person Tracking
- **Two-Stage Association:**
  1. *First Association:* Matches high-confidence detections ($\ge 0.40$) against tracked Kalman predictions using IoU cost matrix.
  2. *Second Association:* Matches remaining unconfirmed tracks against low-confidence detections ($0.10 \le \text{conf} < 0.40$), recovering partially occluded shoppers behind grocery carts.
- **Track Buffer:** Retains state for 30 frames of absence. Dead tracks pruned after 60 frames.

---

### F-03: Virtual Line Crossing Counter
- **Crossing Vector Mathematics:** Evaluates the relative orientation of the previous position $P_{t-1}$ and current position $P_t$ against the virtual boundary line $AB$:
  $$\text{Cross}(A, B, P) = (B_x - A_x)(P_y - A_y) - (B_y - A_y)(P_x - A_x)$$
- A crossing occurs when $\text{sign}(\text{Cross}_{t-1}) \ne \text{sign}(\text{Cross}_t)$ and $|d| > 5\text{px}$ (dead-zone tolerance), preventing jitter from customers oscillating across the line.

---

### F-04: Gaussian Foot-Traffic Heatmap
- **Accumulator Array:** Float32 2D matrix matching camera dimensions ($W \times H$).
- **Kernel Injection:** For each customer ground-contact point $(x, y)$, a pre-computed 2D Gaussian kernel of radius $R=25\text{px}$ and intensity $I=3.0$ is added:
  $$G(dx, dy) = I \cdot \exp\left(-\frac{dx^2 + dy^2}{2\sigma^2}\right)$$
- **Colormap Blending:** Normalized and blended with the live frame using OpenCV `cv2.applyColorMap(..., cv2.COLORMAP_JET)`.

---

### F-05: Cashier Queue Monitor
- Monitors normalized polygon surrounding register lanes.
- Computes real-time occupancy. If $\text{queue\_count} \ge \text{QUEUE\_ALERT\_THRESHOLD}$ (default 3 persons), triggers an instantaneous queue alert flag broadcast over WebSocket.

---

### F-06: Zone Dwell-Time Engine
- **Point-in-Polygon (Ray Casting):** Determines whether customer bottom-center $(x, y)$ resides within zone vertices.
- **Elapsed Real Timestamp Dwell:** $\Delta t = t_{\text{exit}} - t_{\text{enter}}$, immune to video framerate drops.
- **Boundary Hysteresis Grace Window (2.0s):** Candidate exits enter `_pending_exits`. Re-entering within 2.0s cancels the exit and preserves the active visit record.
- **Track Interruption Watchdog (5.0s):** Finalizes interrupted visits when a track is lost.

---

### F-07: Explainable Bottleneck Mapper
- **Multi-Signal Congestion:** Evaluates occupancy ratio ($\ge 1.0\times$), lingering counts, and a $4.0\text{s}$ persistence window.
- **Audit Evidence Array:** Generates transparent explanations:
  `["Capacity exceeded: 4/3 (133%)", "Sustained for 5.0s (threshold: 4.0s)"]`
- **Contextual Recommendation:** Returns operational instructions for floor managers.

---

### F-08: Flow Friction Score Engine (0–100)
$$\text{Score} = \min\left(100.0, \frac{0.40 \cdot S_{\text{occ}} + 0.40 \cdot S_{\text{dwell}} + 0.20 \cdot S_{\text{queue}}}{1.0}\right)$$
Where:
- $S_{\text{occ}} = \min(100, \text{CongestionRatio} \times 100)$
- $S_{\text{dwell}} = \min(100, (\text{ActiveDwellAvg} / \text{AlertSeconds}) \times 100)$
- $S_{\text{queue}} = \min(100, (\text{QueueCount} / \text{Threshold}) \times 100)$

---

### F-09: Normalized Zone Transition Matrix
- Tracks movement sequences between primary zones: $i \to j$.
- Idempotent: successive frames in zone $i$ do not increment counts.
- Hallway retention: walking across unzoned areas preserves origin zone until a new primary zone is reached.
- Computes $P(j \mid i) = \frac{N_{ij}}{\sum_k N_{ik}}$. Flags $N < 5$ as statistically insufficient.

---

### F-10: What-If Layout Simulator & Scenario Comparison
- **AABB Collision Detection:** Flags overlapping physical fixtures with red dashed outlines and warning banners.
- **Aisle Clearance Metric:** Evaluates distance from zone centroids to closest fixture ($d_{\text{clearance}}$).
- **Bottleneck Risk Index (BRI):** Predicts risk tier (`LOW`/`MEDIUM`/`HIGH`/`CRITICAL`) and localized dwell impacts.
- **Zero-Baseline Division Guards:** Outputs `"N/A (baseline is 0)"` or `"0.0%"` when baseline metric is 0.
