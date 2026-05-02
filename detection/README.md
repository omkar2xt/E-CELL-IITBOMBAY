# detection

Week 1 of the Retail Intelligence System. This module handles real-time person detection from video or webcam using YOLO11.

---

## What This Module Does

- Reads frames from a video file or webcam stream
- Detects every person in each frame using YOLO11
- Draws bounding boxes with confidence scores
- Displays live person count and FPS in an info panel
- Optionally saves the annotated output to a video file

This module is intentionally scoped to detection only. Tracking, heatmap, and analytics are added in later weeks on top of this foundation.

---

## Project Structure

```
detection/
├── main.py          # Entry point. Run this.
├── detector.py      # YOLO11 wrapper - PersonDetector class
├── visualizer.py    # All drawing logic - bounding boxes, info panel
├── config.py        # All settings in one place
└── requirements.txt # Python dependencies
```

---

## Setup

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

YOLO11 model weights (~6MB for nano) will be downloaded automatically on first run.

**2. Run with webcam**

```bash
python main.py --source 0
```

**3. Run with a video file**

```bash
python main.py --source path/to/video.mp4
```

**4. Save annotated output to file**

```bash
python main.py --source path/to/video.mp4 --save
```

**5. Override confidence threshold at launch**

```bash
python main.py --source 0 --conf 0.35
```

---

## Keyboard Controls

| Key | Action |
|-----|--------|
| `Q` or `ESC` | Quit |
| `P` | Pause / Resume |
| `+` | Increase confidence threshold by 0.05 |
| `-` | Decrease confidence threshold by 0.05 |
| `S` | Save screenshot of current frame |

Threshold changes with `+` / `-` take effect immediately without restarting.

---

## Configuration

All settings live in `config.py`. Key options:

| Setting | Default | Description |
|---------|---------|-------------|
| `MODEL_NAME` | `yolo11n.pt` | Model size. `n` = nano (fastest), `s/m/l` = larger/more accurate |
| `CONFIDENCE_THRESHOLD` | `0.4` | Min score to count as a detection |
| `VIDEO_SOURCE` | `0` | Default source if no `--source` arg given |
| `SAVE_OUTPUT` | `False` | Save output video |
| `DISPLAY_FPS` | `True` | Show FPS counter |
| `DISPLAY_CONFIDENCE` | `True` | Show confidence score on each box |

### Choosing a model size

```
yolo11n.pt   nano    ~6MB    fastest, good for CPU-only machines
yolo11s.pt   small   ~22MB   balanced
yolo11m.pt   medium  ~52MB   better accuracy, needs decent GPU
yolo11l.pt   large   ~87MB   high accuracy, GPU recommended
```

For development and testing, start with `yolo11n.pt`.

---

## Validation Checklist

Before moving on to Week 2 (tracking + counting), confirm all of these work:

- [ ] Bounding boxes appear around every visible person
- [ ] No significant false positives (chairs, bags, etc. should not be detected)
- [ ] FPS stays above 15 on your machine
- [ ] `+` / `-` keys adjust threshold in real time
- [ ] `S` key saves a screenshot correctly
- [ ] `--save` flag produces a valid output video file

If FPS is too low, switch to `yolo11n.pt` in `config.py`. If false positives are high, raise `CONFIDENCE_THRESHOLD` to `0.5` or `0.6`.

---

## How Detection Works (Quick Summary)

YOLO11 processes each frame as a grid. For each cell, it predicts:
1. Is there an object here?
2. What class is it? (we filter for `class 0 = person` only)
3. What are the bounding box coordinates?

Output is a list of `Detection` objects, each containing:
- `bbox` - coordinates `[x1, y1, x2, y2]` in pixels
- `confidence` - float between 0.0 and 1.0
- `center` - midpoint of the box (used by heatmap in Week 3)

Detection alone cannot count people accurately across time. That requires tracking, which is added in Week 2.

---

## Dataset Recommendations

| Dataset | Use Case | Source |
|---------|----------|--------|
| Mall Dataset | Main test video, fixed overhead CCTV of mall | Kaggle: `chaozhuang/mall-dataset` |
| Pedestrian Dataset | Entry/exit door testing | Kaggle: `smeschke/pedestrian-dataset` |
| Crowd Counting Dataset | Dense crowd scenarios | Kaggle: `trainingdatapro/crowd-counting-dataset` |

You do not need to train the model. YOLO11 is pre-trained on COCO which includes thousands of person images. The datasets above are used as test videos only.

---

## Next Steps

Week 2 adds ByteTrack multi-person tracking on top of this detection pipeline:
- Each person gets a persistent Track ID across frames
- Virtual line crossing for accurate entry/exit counting
- Trajectory visualization

The `Detection` dataclass in `detector.py` is already designed to accept a `track_id` field, so Week 2 integration requires no changes to this module.