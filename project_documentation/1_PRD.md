# StorePulse AI — Product Requirements Document (PRD)

**Product Name:** StorePulse AI  
**Developer & Architect:** Omkar Gurav  
**Hackathon:** Everseen Computer Vision AI Hackathon  
**Problem Statement 3:** Dwell-Time & Bottleneck Mapper  
**Version:** 1.0.0  
**Status:** Certified / Complete  

---

## 1. Executive Summary

Modern brick-and-mortar retail operators manage complex spatial environments without real-time quantitative visibility into customer movement dynamics, dwell patterns, and localized congestion bottlenecks. Traditional store layout optimization relies on anecdotal observations, manual clicker counts, or disruptive trial-and-error remodeling.

**StorePulse AI** solves this critical operational challenge through an intelligent, end-to-end edge computer vision pipeline paired with an interactive **What-If Layout Simulator**. By converting existing overhead or angled CCTV feeds into anonymous spatial intelligence, StorePulse AI enables retailers to observe empirical customer dwell and flow friction in real time, simulate virtual store reconfigurations, and evaluate before-and-after operational impacts before investing capital into physical construction.

---

## 2. Problem Statement & Market Pain Points

### 2.1 The Core Problem
In physical grocery, supermarket, and department stores:
- **Invisible Bottlenecks:** Register queues spill into promo endcaps, blocking high-margin aisles without management awareness.
- **Unverified Dwell Times:** Merchandisers cannot distinguish between high-engagement browsing (positive dwell) and aisle constriction stalls (frustrated dwell).
- **Risky Remodeling:** Repositioning shelving displays and checkouts often produces unforeseen pinch-points, increasing customer friction and reducing basket size.
- **Privacy Liabilities:** Conventional retail tracking systems risk violating GDPR, CCPA, and customer trust through facial recognition or persistent biometric tracking.

### 2.2 Target Personas
1. **Store Operations Manager:** Needs instant alerts when checkout queues or department aisles exceed capacity for $\ge 4.0\text{s}$ to redeploy floor staff.
2. **Visual Merchandiser / Category Planner:** Needs empirical zone transition probabilities and dwell heatmaps to determine optimal promotional endcap placements.
3. **Retail Executive / Store Designer:** Needs a predictive "What-If" digital twin to evaluate layout alterations against baseline walkability and conflict scores.

---

## 3. Product Goals & Objectives

| Objective | Target Metric | Engineering Validation |
|---|---|---|
| **Real-Time Edge Detection & Tracking** | $\ge 8.0\text{ FPS}$ on standard CPU hardware | YOLO11n + ByteTrack achieving ~120 ms/frame (~8.3 FPS) on CPU |
| **Dwell Time Precision** | Elapsed timestamp precision ($< 0.1\text{s}$ drift) | Independent of framerate variations; zero boundary jitter |
| **Anti-Flicker Bottleneck Alerts** | Zero false alarms on transient ($< 4\text{s}$) spikes | 4.0s persistence window and 1.5s cooldown hysteresis |
| **Spatial Drag Quantification** | Standardized 0–100 index | Formulated explainable Flow Friction Score combining occupancy, dwell, and queues |
| **Interactive Layout Simulation** | Instant heuristic feedback ($< 200\text{ms}$) | AABB fixture overlap collision checks, Manhattan distance walkability, and zone clearance calculations |
| **Privacy Compliance** | Zero biometrics / facial recognition | Ephemeral integer tracking IDs only, purged upon frame exit |

---

## 4. Key Functional Requirements

### 4.1 Vision & Tracking Pipeline
- **FR-1.1:** Must ingest standard CCTV RTSP streams, recorded video files (`.mp4`/`.avi`), and physical webcams.
- **FR-1.2:** Must execute person-only detection filtered to COCO Class 0 (`person`) with confidence threshold $\ge 0.40$.
- **FR-1.3:** Must maintain persistent numeric track IDs across frames using ByteTrack Kalman filtering and IoU association.
- **FR-1.4:** Must provide bidirectional virtual line crossing counts (In/Out) with dead-zone hysteresis ($5\text{px}$).
- **FR-1.5:** Must generate a real-time 2D Gaussian foot-traffic heatmap.

### 4.2 Dwell-Time & Bottleneck Intelligence
- **FR-2.1:** Must support user-defined convex and non-convex polygonal zones configured via normalized coordinates ($[0.0, 1.0]$).
- **FR-2.2:** Must calculate dwell time using elapsed real timestamps ($\Delta t = t_{\text{exit}} - t_{\text{enter}}$).
- **FR-2.3:** Must enforce a $2.0\text{s}$ boundary hysteresis grace window to eliminate jitter when customers linger on zone borders.
- **FR-2.4:** Must detect track loss and finalize interrupted visits after $5.0\text{s}$ of camera absence.
- **FR-2.5:** Must provide separate real-time metrics for active in-progress visits and completed historical visits.
- **FR-2.6:** Must generate explainable bottleneck alerts based on occupancy ratio ($\ge 1.0\times$), lingering counts, and a $4.0\text{s}$ persistence window.

### 4.3 Zone Transition Probability Matrix
- **FR-3.1:** Must record transitions between zones ($i \to j$) based on sequential person movement.
- **FR-3.2:** Must prevent duplicate transitions on consecutive frames inside the same zone.
- **FR-3.3:** Must preserve origin zone state across unzoned hallways to capture genuine store traversals.
- **FR-3.4:** Must compute normalized conditional routing probabilities: $P(j \mid i) = \frac{N_{ij}}{\sum_k N_{ik}}$.
- **FR-3.5:** Must flag samples with $N < 5$ as statistically insufficient and provide explicit visual indicators.

### 4.4 What-If Layout Simulator & Scenario Comparison
- **FR-4.1:** Must provide an interactive SVG canvas ($800\times500\text{px}$) with $40\text{px}$ grid snapping.
- **FR-4.2:** Must allow adding, dragging, resizing, rotating ($90^\circ$), cloning, and deleting shelves, checkouts, displays, and obstacles.
- **FR-4.3:** Must provide a 20-state undo stack and one-click "Reset to Baseline".
- **FR-4.4:** Must execute real-time Axis-Aligned Bounding Box (AABB) fixture collision detection and display prominent obstruction warnings.
- **FR-4.5:** Must simulate layout changes using empirical transition probabilities (when $N \ge 5$) or documented category demand priors.
- **FR-4.6:** Must compute walking distance, space utilization, route conflict scores, and zone-by-zone aisle clearance.
- **FR-4.7:** Must generate side-by-side scenario comparison reports with division-by-zero math safety and clear labeling distinguishing `[MEASURED REAL]` from `[HEURISTIC ESTIMATE]`.

---

## 5. Non-Functional Requirements

- **NFR-1 (Performance):** Backend REST APIs must respond in $< 50\text{ms}$; WebSocket telemetry broadcast interval set to 5 frames.
- **NFR-2 (Reliability):** Auto-reconnection with exponential backoff on dropped RTSP/camera feeds; clean looping on video files.
- **NFR-3 (Privacy):** No face detection, facial embeddings, gender classification by default, or persistent biometric storage.
- **NFR-4 (Extensibility):** Modular architecture allowing integration with Point-of-Sale (POS) data and external MCP tooling.
- **NFR-5 (Testability):** 100% automated test pass rate across unit, integration, and API contract tests.

---

## 6. Success Metrics & KPIs

1. **System Uptime & Stability:** Zero unhandled exceptions or memory leaks during continuous multi-hour CCTV execution.
2. **Measurement Accuracy:** 100% deterministic reproducibility across dwell calculations and transition matrices.
3. **Evaluation Readiness:** 100% test suite pass rate (46 passing tests) and error-free frontend production bundle.
