# Retail Intelligence System

A real-time video analytics platform for retail stores. Counts visitors, maps popular zones, monitors queue lengths, and estimates visitor demographics, all without storing personal identity.

Built as a 4-week project covering production-ready computer vision concepts: object detection, multi-person tracking, heatmap generation, zone analytics, and a live streaming dashboard.

---

## Project Structure

```
retail_analytics/
├── detection/          Week 1 - Person detection with YOLO11
├── tracking/           Week 2 - Multi-person tracking + entry/exit counting
├── analytics/          Week 3 - Heatmap, queue monitor, demographic estimation
└── dashboard/          Week 4 - FastAPI backend + React live dashboard
```

Each module is standalone and runnable on its own. Later modules import components from earlier ones rather than rewriting them.

---

## Features

| Feature | Module | Status |
|---------|--------|--------|
| Person detection | `detection/` | Week 1 |
| Multi-person tracking (ByteTrack) | `tracking/` | Week 2 |
| Entry / exit counting | `tracking/` | Week 2 |
| Heatmap of popular zones | `analytics/` | Week 3 |
| Queue length monitoring | `analytics/` | Week 3 |
| Age / gender estimation (no identity stored) | `analytics/` | Week 3 |
| Real-time WebSocket backend | `dashboard/` | Week 4 |
| React live dashboard | `dashboard/` | Week 4 |
| Daily / weekly report export | `dashboard/` | Week 4 |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Detection | YOLO11 (Ultralytics) |
| Tracking | ByteTrack |
| Video processing | OpenCV |
| Demographic estimation | DeepFace (age/gender only, no face recognition) |
| Deep learning | PyTorch |
| Backend | FastAPI + WebSocket |
| Frontend | React + Chart.js |

---

## Pipeline Overview

```
Video / Webcam
      |
      v
  Pre-processing          resize, normalize frames
      |
      v
  YOLO11 Detection        locate every person in the frame
      |
      v
  ByteTrack               assign persistent Track ID to each person
      |
      +----------+----------+----------+
      |          |          |          |
      v          v          v          v
  Counting   Heatmap    Queue      DeepFace
  (line      (position  (zone      (age/gender
  crossing)  accumulate) density)   estimation)
      |          |          |          |
      +----------+----------+----------+
                 |
                 v
          FastAPI + WebSocket
                 |
                 v
          React Dashboard
```

---

## Modules

### Week 1 - detection/

Reads video frames and detects every person using YOLO11. Outputs bounding boxes with confidence scores and a live person count.

### Week 2 - tracking/

Adds ByteTrack on top of detection. Each person receives a persistent Track ID that stays consistent across frames. A virtual line at the entrance counts entries and exits accurately without double-counting.

### Week 3 - analytics/

Three analytics layers built on top of tracking output:

- **Heatmap**: accumulates foot traffic positions across the session into a colored overlay showing popular zones
- **Queue monitor**: counts persons inside a defined zone (e.g. checkout area) and alerts when the queue exceeds a threshold
- **Demographic estimation**: DeepFace estimates age range and gender from detected faces. No face embeddings or identities are stored; only aggregate statistics are kept

### Week 4 - dashboard/

Wraps the full pipeline in a FastAPI server with a WebSocket endpoint. A React frontend connects and receives live data to display:

- Real-time person count
- Heatmap overlay on a store floor plan
- Demographic bar charts
- Queue length graph
- Daily and weekly report export (PDF / CSV)

---

## Getting Started

Each module has its own `requirements.txt` and `README.md`. Start with Week 1 and validate it before moving on.

```bash
# Week 1
cd detection
pip install -r requirements.txt
python main.py --source 0           # webcam
python main.py --source video.mp4   # video file
```

Full instructions for each week are in the corresponding module README.

---

## Dataset Recommendations

You do not need to train any model. YOLO11 is pre-trained on COCO (which includes persons). Datasets below are used as test videos only.

| Dataset | Purpose | Source |
|---------|---------|--------|
| Mall Dataset | Primary test video, overhead CCTV of mall corridor | Kaggle: `chaozhuang/mall-dataset` |
| Pedestrian Dataset | Entry/exit door counting test | Kaggle: `smeschke/pedestrian-dataset` |
| Crowd Counting Dataset | Dense crowd scenarios | Kaggle: `trainingdatapro/crowd-counting-dataset` |

For queue monitoring (Week 3), no public dataset closely matches a retail checkout area. A short self-recorded clip or a YouTube surveillance video works fine for development purposes.

---

## Privacy Design

This system is designed to analyze behavior without identifying individuals:

- Face recognition is disabled. DeepFace is used for attribute estimation only (age range, gender).
- No face embeddings are stored or logged.
- No individual trajectories are persisted after a session ends.
- Only aggregate statistics (counts, distributions, heatmap density) are written to reports.

---

## CV Concepts Covered

- Object detection (YOLO11, anchor-free detection head)
- Multi-object tracking (ByteTrack, IoU matching, Kalman filter)
- People counting (virtual line crossing with Track ID)
- Heatmap generation (Gaussian accumulation on 2D numpy array)
- Zone analytics (region of interest definition, density threshold)
- Demographic estimation (privacy-preserving facial attribute analysis)
- Real-time video pipeline (frame loop, WebSocket streaming, latency management)

---

## Validation Checklist per Week

**Week 1 complete when:**
- Bounding boxes appear on every visible person
- FPS stays above 15 on target hardware
- No significant false positives at chosen confidence threshold

**Week 2 complete when:**
- Track IDs stay consistent as people move across frames
- Entry/exit counter does not double-count the same person
- ID is recovered after brief occlusion

**Week 3 complete when:**
- Heatmap visually matches high-traffic zones in the video
- Queue alert triggers correctly when zone exceeds person threshold
- Demographic chart updates every few seconds without crashing pipeline FPS

**Week 4 complete when:**
- Dashboard updates in real time with less than 1 second lag
- All charts reflect live data from the pipeline
- Report export produces a valid file with correct aggregated stats