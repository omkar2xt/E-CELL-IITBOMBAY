# analytics

This module adds three analytics layers on top of the tracking pipeline: heatmap generation, zone-based queue monitoring, and demographic estimation (age range + gender).

---

## What This Module Does

- Generates a real-time cumulative heatmap showing the most visited areas of the store
- Monitors defined zones (e.g. checkout area) and alerts when occupancy exceeds a threshold
- Estimates visitor age range and gender distribution using OpenCV DNN - without storing any identity
- Displays a live demographic panel with bar charts for gender and age groups
- Exports heatmap snapshots and prints a session summary on exit

---

## Project Structure

```
analytics/
├── main.py          # Entry point. Run this.
├── heatmap.py       # Gaussian accumulation heatmap generator
├── queue_monitor.py # Zone-based occupancy counter and alert system
├── demographic.py   # Age/gender estimator (OpenCV DNN, background thread)
├── visualizer.py    # All drawing logic for analytics overlays
├── config.py        # All settings (imports + extends tracking/config.py)
├── models/          # Caffe model weights (auto-downloaded on first run)
└── requirements.txt # Python dependencies
```

Depends on `detection/` at `../detection/` and `tracking/` at `../tracking/` for imports.

---

## Setup

This module reuses the venv from the detection step.

**1. Activate the existing venv**

```bash
source ../detection/venv/bin/activate
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

> On first run, `demographic.py` will automatically download the Caffe model weights to `analytics/models/` (~88MB total). No manual download needed.

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
| `HEATMAP_RADIUS` | `25` | Gaussian kernel radius in pixels |
| `HEATMAP_ALPHA` | `0.45` | Heatmap overlay opacity (0.0 to 1.0) |
| `HEATMAP_COLORMAP` | `COLORMAP_JET` | OpenCV colormap for rendering |
| `HEATMAP_NORMALIZE_INTERVAL` | `15` | Frames between normalization passes |

Tuning tips: if the heatmap saturates too quickly (everything red), lower `HEATMAP_INTENSITY`. If it is too slow to form, increase it.

### Queue zone settings

The checkout monitoring zone is defined as a ratio rectangle in `config.py`:

```python
# Format: (x1, y1, x2, y2) as ratios of frame size (0.0 – 1.0)
QUEUE_ZONE = (0.13, 0.15, 0.37, 0.50)
QUEUE_ALERT_THRESHOLD = 3   # persons inside zone before alert triggers
```

Using ratios instead of pixel coordinates means the zone works correctly at any video resolution. To calibrate: run the pipeline once, use `E` to export a heatmap snapshot, open it, measure pixel positions of your target area, then convert to ratios by dividing by frame width/height.

### Demographic settings

| Setting | Default | Description |
|---------|---------|-------------|
| `DEMO_ANALYSIS_INTERVAL` | `15` | Run estimator every N frames |
| `DEMO_HISTORY_SIZE` | `50` | Rolling window of samples for distribution |
| `DEMO_MIN_PERSON_HEIGHT` | `80` | Min pixel height before attempting analysis |

---

## Demographic Estimation - Implementation Notes

### Why we switched from DeepFace to OpenCV DNN

The original design used **DeepFace** for age and gender estimation. DeepFace is a high-level wrapper around several state-of-the-art face analysis models and delivers good accuracy.

However, DeepFace requires **TensorFlow** as its backend, and TensorFlow **does not support Python 3.14** (as of mid-2025). Attempting to install `deepface` on the system Python 3.14 environment results in:

```
ERROR: Cannot install deepface because tensorflow has no compatible version
       for Python 3.14
```

Installing a separate Python 3.11/3.12 environment is possible in theory, but Fedora's mirror servers were unavailable at the time of development, making that path impractical.

### Current approach - OpenCV DNN + Caffe models

We replaced DeepFace with a **TensorFlow-free** implementation using OpenCV's built-in DNN module and the classic Caffe models from the paper:

> **Age and Gender Classification Using Convolutional Neural Networks**  
> Gil Levi & Tal Hassner, IEEE Workshop on Analysis and Modeling of Faces and Gestures (AMFG), 2015.

These models are lightweight (~44MB each) and run entirely within OpenCV - no separate ML framework required. The trade-off is lower accuracy compared to modern deep learning approaches, but the result is still useful for aggregate demographic trend analysis in a retail context.

**How it works:**

1. **Face detection** - OpenCV's built-in Haar Cascade (`haarcascade_frontalface_default.xml`, zero download required)
2. **Age classification** - Caffe model predicts one of 8 age buckets: `(0-2)`, `(4-6)`, `(8-12)`, `(15-20)`, `(25-32)`, `(38-43)`, `(48-53)`, `(60+)`
3. **Gender classification** - Caffe model predicts `Male` or `Female`

Models are automatically downloaded to `analytics/models/` on first run via `gdown` (Google Drive) for the `.caffemodel` files and direct HTTP for the `.prototxt` config files.

**Privacy guarantees are unchanged:**
- Face crops are processed in memory and immediately discarded
- No face embeddings are stored
- No mapping between Track IDs and demographic results
- Only aggregate distribution statistics are kept

---

## How Heatmap Works

A `numpy` float32 array the same size as the video frame is maintained across the session. Every frame, for each tracked person their `bottom_center` position is used to add a pre-computed Gaussian kernel to the array.

For rendering, the array is normalized to 0–255 and a colormap is applied. Only pixels above a threshold are blended onto the frame, so cold areas remain transparent.

The `bottom_center` of each person's bounding box is used rather than the box center. This produces a heatmap of where people stand and walk, which is more relevant for floor-plan analysis.

---

## How Zone Monitoring Works

The zone is a rectangle defined in `config.py` as ratios. Every frame, the `bottom_center` of each tracked person is checked against the zone using a point-in-rectangle test. A person is counted only if their foot position falls inside - this prevents double-counting at zone boundaries.

---

## Session Summary

When the pipeline exits (Q, ESC, or Ctrl+C), a summary is printed:

```
SESSION SUMMARY
  Total IN        : 42
  Total OUT       : 38
  Final Occupancy : 4

  Queue Zone:
    Peak count   : 5
    Alert count  : 2

  Demographics:
    Samples   : 67
    Gender    : {'Female': 54.0, 'Male': 46.0}
    Age groups: {'(25-32)': 38.8, '(15-20)': 22.4, '(38-43)': 19.4}
```

---

## Validation Checklist

- [ ] Heatmap overlay appears and fills in over time as people move
- [ ] High-traffic areas turn yellow/red, low-traffic areas stay blue/green
- [ ] `H` key toggles heatmap on and off without restarting
- [ ] Queue zone rectangle appears on frame at correct position
- [ ] Queue count updates correctly as people enter and leave the zone
- [ ] Alert banner appears when queue exceeds threshold
- [ ] Demographic panel appears after enough samples accumulate
- [ ] Gender and age bars update over time
- [ ] Session summary prints correct stats on exit
- [ ] `--save-heatmap` flag saves a valid image file

If demographic estimation is slow and dropping FPS, increase `DEMO_ANALYSIS_INTERVAL` to 30–60, or run with `--no-demo` to disable it entirely.