# analytics

Week 3 of the Retail Intelligence System. This module adds three analytics layers on top of the tracking pipeline: heatmap generation, zone-based queue monitoring, and privacy-preserving demographic estimation.

---

## What This Module Does

- Generates a real-time cumulative heatmap showing the most visited areas of the store
- Monitors defined zones (e.g. checkout area) and alerts when occupancy exceeds a threshold
- Estimates visitor age range and gender distribution using DeepFace, without storing any identity
- Displays a live demographic panel with bar charts for gender and age groups
- Exports heatmap snapshots and prints a session summary on exit

This module builds on `detection/` and `tracking/`. The venv from Week 1 is reused.

---

## Project Structure

```
analytics/
├── main.py          # Entry point. Run this.
├── heatmap.py       # Gaussian accumulation heatmap generator
├── zone_monitor.py  # Zone-based occupancy counter and alert system
├── demographic.py   # DeepFace age/gender wrapper (background thread)
├── visualizer.py    # All drawing logic for analytics overlays
├── config.py        # All settings (imports + extends tracking/config.py)
└── requirements.txt # Python dependencies
```

Depends on `detection/` at `../detection/` and `tracking/` at `../tracking/` for imports.

---

## Setup

This module reuses the venv from Week 1.

**1. Activate the existing venv**

```bash
source ../detection/venv/bin/activate
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

DeepFace and tf-keras are the new additions. They are around 500MB total on first install due to model weights being downloaded automatically on first use.

**3. Run with a video file**

```bash
python main.py --source path/to/video.mp4
```

**4. Run with webcam**

```bash
python main.py --source 0
```

**5. Save annotated output**

```bash
python main.py --source video.mp4 --save
```

**6. Run without GUI (headless)**

```bash
python main.py --source video.mp4 --headless
```

**7. Export heatmap snapshot on exit**

```bash
python main.py --source video.mp4 --save-heatmap
```

**8. Skip demographic estimation (faster)**

```bash
python main.py --source video.mp4 --no-demo
```

---

## Keyboard Controls

| Key | Action |
|-----|--------|
| `Q` or `ESC` | Quit and print session summary |
| `P` | Pause / Resume |
| `H` | Toggle heatmap overlay on/off |
| `R` | Reset counter and heatmap |
| `E` | Export heatmap snapshot to file right now |
| `S` | Save screenshot of current frame |
| `+` | Increase confidence threshold by 0.05 |
| `-` | Decrease confidence threshold by 0.05 |

---

## Configuration

All settings live in `config.py`. This file imports everything from `tracking/config.py` and adds analytics-specific options.

### Heatmap settings

| Setting | Default | Description |
|---------|---------|-------------|
| `HEATMAP_INTENSITY` | `3` | Heat added per person per frame |
| `HEATMAP_RADIUS` | `30` | Gaussian kernel radius in pixels |
| `HEATMAP_DECAY` | `0.998` | Decay factor per frame (1.0 = no decay) |
| `HEATMAP_ALPHA` | `0.45` | Heatmap overlay opacity (0.0 to 1.0) |
| `HEATMAP_COLORMAP` | `COLORMAP_JET` | OpenCV colormap for rendering |

Tuning tips: if the heatmap saturates too quickly (everything red), lower `HEATMAP_INTENSITY` or increase `HEATMAP_DECAY` toward 1.0. If the heatmap is too slow to form, do the opposite.

### Zone settings

Zones are defined in `config.py` as a dict of name to rectangle coordinates:

```python
ZONES = {
    "CASHIER":  (430, 280, 630, 470),
    "ENTRANCE": (10,  200, 160, 470),
}
```

Coordinates are `(x1, y1, x2, y2)` in pixels. Adjust these to match your actual video layout. Run the pipeline once, note the pixel positions of the areas you care about, then update `config.py`.

Alert thresholds per zone:

```python
ZONE_ALERT_THRESHOLD = {
    "CASHIER":  3,
    "ENTRANCE": 5,
}
```

### Demographic settings

| Setting | Default | Description |
|---------|---------|-------------|
| `DEMO_INTERVAL` | `15` | Run DeepFace every N frames |
| `DEMO_HISTORY_SIZE` | `100` | Rolling window of samples for distribution |
| `DEMO_DETECTOR_BACKEND` | `"opencv"` | Face detector backend inside DeepFace |

Backend options: `opencv` (fastest), `ssd`, `mtcnn`, `retinaface` (most accurate but slowest). For development use `opencv`. Switch to `retinaface` for production accuracy.

---

## How Heatmap Works

A numpy float32 array the same size as the video frame is maintained across the session. Every frame, for each tracked person their `bottom_center` position is used to add a Gaussian kernel to the array at that location. The kernel is pre-computed once at startup.

After adding new heat, the entire array is multiplied by the decay factor (slightly less than 1.0), causing older heat to slowly fade. This means the heatmap reflects recent activity more strongly than very old activity.

For rendering, the array is normalized to 0-255 and a colormap is applied. Only pixels above a threshold are blended onto the frame, so cold areas remain transparent and do not obscure the video.

The `bottom_center` of each person's bounding box is used rather than the box center. This produces a heatmap of where people stand and walk, not where their torsos are in the image, which is more relevant for floor-plan analysis.

---

## How Zone Monitoring Works

Each zone is a rectangle defined in config. Every frame, the `bottom_center` of each tracked person is checked against each zone rectangle using a simple point-in-rectangle test. A person is counted in a zone if and only if their foot position falls inside it.

Using a single point rather than bounding box overlap prevents double-counting when a person stands at the boundary of two adjacent zones.

`ZoneStats` tracks current count, peak count, and accumulated person-seconds (total time people have spent in the zone). These are included in the session summary on exit.

---

## How Demographic Estimation Works

DeepFace is run every `DEMO_INTERVAL` frames on face crops extracted from tracked person bounding boxes. The top 40% of each bounding box is cropped as an approximation of the head region and passed to DeepFace.

DeepFace is called with `actions=["age", "gender"]` only. Face recognition and identity functions are not called. Face embeddings are never stored. The crop is passed in memory and discarded immediately after analysis.

Results are bucketed into age groups (under 18, 18-24, 25-34, etc.) and stored as aggregate counts in a rolling deque. The panel displays percentage distributions across the rolling window, not individual results.

DeepFace runs in a background thread so the main pipeline is never blocked. If a previous analysis is still running when the next interval arrives, the new one is skipped rather than queued.

If DeepFace is not installed, the module initializes successfully with demographics disabled. All other features work normally.

---

## Privacy Design

- DeepFace is called for attribute estimation only (`age`, `gender`). The `identity` action is never used.
- No face embeddings are computed or stored.
- No association is made between a Track ID and demographic results. Results are purely aggregate.
- Face crops exist only in memory during the DeepFace call and are not written to disk.
- Only distribution statistics (e.g. "35% age 25-34") are retained.

---

## Session Summary

When the pipeline exits (Q, ESC, or Ctrl+C), a summary is printed:

```
SESSION SUMMARY
  Total IN        : 42
  Total OUT       : 38
  Final Occupancy : 4

  Zone Stats:
    CASHIER
      Peak count   : 5
      Person-secs  : 312.4s
    ENTRANCE
      Peak count   : 8
      Person-secs  : 89.1s

  Demographics:
    Samples   : 67
    Gender    : {'Woman': 54.0, 'Man': 46.0}
    Age groups: {'25-34': 38.8, '18-24': 22.4, '35-44': 19.4}
```

---

## Validation Checklist

Before moving on to Week 4 (FastAPI backend + React dashboard), confirm all of these work:

- [ ] Heatmap overlay appears and fills in over time as people move
- [ ] High-traffic areas turn yellow/red, low-traffic areas stay blue/green
- [ ] Heatmap persists and accumulates (does not reset each frame)
- [ ] `H` key toggles heatmap on and off without restarting
- [ ] Zone rectangles appear on frame at correct positions
- [ ] Zone count updates correctly as people enter and leave the zone
- [ ] Alert banner appears at the bottom when a zone exceeds its threshold
- [ ] Demographic panel appears in top-right after enough samples
- [ ] Gender and age bars update over time
- [ ] Session summary prints correct stats on exit
- [ ] `--save-heatmap` flag saves a valid image file

If DeepFace is slow and dropping FPS, increase `DEMO_INTERVAL` to 30 or 60, or run with `--no-demo` to disable it entirely.

If zone counts are inaccurate, adjust zone coordinates in `config.py` to better match your video layout. Run once with a paused frame and use `E` to export a heatmap snapshot to use as a reference for coordinate calibration.

---

## Next Steps

Week 4 wraps this entire pipeline in a FastAPI backend with a WebSocket endpoint and a React live dashboard:

- FastAPI runs the analytics pipeline in a background process
- Each frame's analytics data (counts, zone stats, demographics) is serialized to JSON
- WebSocket pushes updates to the React frontend every second
- React renders live charts, heatmap overlay on a store floor plan, and queue status
- Daily and weekly report export is added as a REST endpoint