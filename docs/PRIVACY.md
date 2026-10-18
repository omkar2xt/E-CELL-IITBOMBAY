# StorePulse AI — Privacy & Responsible Analytics Policy
**Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator  
**Developer / Owner:** Omkar Gurav  
**Status:** Active  

---

## 1. Core Principles

StorePulse AI is engineered to provide actionable physical retail business intelligence **without compromising individual shopper privacy**. We adhere strictly to Privacy by Design (PbD) principles:

1. **Zero Facial Recognition or Biometric ID:** No face recognition, facial embeddings, face prints, or identity matching technologies exist in the system.
2. **Short-Lived Ephemeral Tracking:** Track IDs assigned by ByteTrack are transient integer counters (e.g., Track #4) kept strictly in volatile RAM. They are purged automatically upon frame exit or tracking loss.
3. **No Video Recording or Storage:** Camera video streams are analyzed frame-by-frame in real-time memory. Raw video frames, CCTV footage, and recordings are never saved to disk or persistent databases.
4. **Aggregate Spatial Statistics Only:** Downstream metrics (occupancy counts, average dwell seconds, heatmaps, flow transitions) represent aggregated statistical distributions, never individual customer dossiers.
5. **Privacy-Preserving Defaults:** Demographics estimation (age/gender) is disabled by default via `DEMOGRAPHICS_ENABLED=false` in the configuration.

---

## 2. Data Life Cycle

| Data Type | Ingest Method | In-Memory Lifetime | Stored on Disk? |
|-----------|---------------|-------------------|-----------------|
| Raw Video Frames | RTSP / Webcam / File | Single frame loop cycle | **Never** |
| Person Detections | YOLO11 Bounding Boxes | $< 50$ milliseconds | **Never** |
| Tracking IDs | ByteTrack Kalman Filter | Duration of presence in frame | **Never** |
| Zone Visits | Timestamped in/out | Duration of presence in zone | **Never** (cleared on exit) |
| Aggregate Metrics | Counts, Dwell Avgs, Heatmaps | Session duration | Aggregates only |
| Layout Configurations | User floor plans (JSON) | Persistent | Yes (geometric shapes only) |

---

## 3. Demographics Estimation Notice

The inherited repository contains an experimental OpenCV DNN + Caffe module for estimating age brackets and gender from face crops.
- In StorePulse AI, **this module is turned OFF by default** (`DEMOGRAPHICS_ENABLED=false`).
- If toggled on in settings for statistical demographic research, it produces purely aggregate bucket counts (e.g. `18-25: 12%`, `25-35: 45%`).
- No facial biometric templates, photos, or personal identities are extracted or saved.

---

## 4. Responsible AI & Transparency

- **Heuristic Layout Simulator Disclaimer:** All layout simulation outputs (walking distance changes, friction reduction estimates) are heuristic mathematical approximations based on spatial geometry. They do not claim to predict individualized human behavior with clinical certainty.
- **Decision-Support Classification:** Flow Friction Scores and layout comparisons are decision-support tools meant to aid human store managers in spatial planning, not autonomous execution engines.
