# tracking

Week 2 of the Retail Intelligence System. This module adds ByteTrack multi-person tracking and virtual line counting on top of the detection pipeline from Week 1.

---

## What This Module Does

- Assigns a persistent Track ID to each detected person across frames
- Draws trajectory trails showing each person's movement path
- Counts people crossing a virtual line (entry/exit counter)
- Displays live IN / OUT totals and current occupancy estimate
- Flashes a visual alert on every crossing event

This module builds directly on `detection/`. The venv and model weights from Week 1 are reused.

---

## Project Structure

```
tracking/
├── main.py          # Entry point. Run this.
├── tracker.py       # ByteTrack wrapper - PersonTracker class
├── counter.py       # Virtual line crossing logic - LineCounter class
├── visualizer.py    # All drawing logic - boxes, trajectories, line, panel
├── config.py        # All settings (imports + extends detection/config.py)
└── requirements.txt # Python dependencies
```

Depends on `detection/` being present at `../detection/` for config imports.

---

## Setup

This module reuses the venv from Week 1. No need to create a new one.

**1. Activate the existing venv**

```bash
source ../detection/venv/bin/activate
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

scipy is likely already installed as a torch dependency, so this step is usually instant.

**3. Run with webcam**

```bash
python main.py --source 0
```

**4. Run with a video file**

```bash
python main.py --source path/to/video.mp4
```

**5. Save annotated output to file**

```bash
python main.py --source path/to/video.mp4 --save
```

**6. Run without GUI window (headless)**

```bash
python main.py --source path/to/video.mp4 --headless
```

**7. Change counting line orientation**

```bash
# Default: vertical line at center (people walk left/right through it)
python main.py --source video.mp4 --line-orientation horizontal

# horizontal: line at center, people walk up/down through it
python main.py --source video.mp4 --line-orientation vertical
```

---

## Keyboard Controls

| Key | Action |
|-----|--------|
| `Q` or `ESC` | Quit |
| `P` | Pause / Resume |
| `R` | Reset IN / OUT counter |
| `S` | Save screenshot of current frame |
| `+` | Increase confidence threshold by 0.05 |
| `-` | Decrease confidence threshold by 0.05 |

---

## Configuration

All settings live in `config.py`. This file imports everything from `detection/config.py` and adds tracking-specific options below.

### Tracking settings

| Setting | Default | Description |
|---------|---------|-------------|
| `TRACK_THRESH` | `0.4` | Min confidence to assign detection to an active track |
| `MATCH_THRESH` | `0.8` | Min IoU to consider two boxes the same person |
| `TRACK_BUFFER` | `30` | Frames a track survives without a detection before being dropped |
| `FRAME_RATE` | `30` | Source FPS, used by Kalman filter for motion prediction |

### Counting line settings

| Setting | Default | Description |
|---------|---------|-------------|
| `LINE_ORIENTATION` | `horizontal` | `horizontal` = vertical line, people walk left/right. `vertical` = horizontal line, people walk up/down |
| `LINE_CROSSING_TOLERANCE` | `5` | Dead zone width in pixels around the line to prevent jitter counts |

### Line position

By default the line is placed at the center of the frame and auto-calculated from the video resolution at runtime. To set a fixed position, override `LINE_START` and `LINE_END` directly in `config.py`:

```python
LINE_START = (320, 0)    # x=320, top of frame
LINE_END   = (320, 480)  # x=320, bottom of frame
```

---

## How Tracking Works (Quick Summary)

**The core problem:** YOLO detects bounding boxes per frame with no memory. The same person detected in frame 100 and frame 101 are two separate, unrelated detections. Tracking connects them.

**ByteTrack in two steps per frame:**

Step 1 - High-confidence detections are matched to existing active tracks using IoU. If overlap is high enough, the detection inherits the existing Track ID.

Step 2 - Low-confidence detections are matched against tracks that recently lost their detection. This is the key ByteTrack innovation: instead of discarding low-confidence boxes, it tries to use them to re-link lost tracks.

**Kalman Filter** predicts where each tracked person should be in the next frame based on their recent velocity. This prediction is what gets compared against new detections via IoU, not the last known position.

**`persist=True`** in the Ultralytics call is what makes IDs consistent across frames. Without it, IDs reset on every call.

---

## How Counting Works (Quick Summary)

A virtual line divides the frame into side A and side B. For each tracked person, their `bottom_center` (midpoint of the bottom edge of the bounding box) is used as their position reference rather than the full center. This is more accurate because it represents foot position, which is stable even when a person leans or turns.

Every frame, the counter checks which side each Track ID is on. When a Track ID transitions from side A to side B (or B to A), a crossing is recorded. Direction of movement determines whether it is counted as IN or OUT.

A tolerance dead zone around the line prevents the same crossing from being counted multiple times due to jitter.

---

## Occupancy Estimate

The info panel shows an `Occupancy` value calculated as `IN - OUT`. This is an estimate of how many people are currently inside the monitored area. It can go negative if the video does not start from an empty area or if someone exits without being counted entering. Press `R` to reset all counts if needed.

---

## Validation Checklist

Before moving on to Week 3 (heatmap + queue + demographics), confirm all of these work:

- [ ] Each person has a Track ID label that stays consistent as they move
- [ ] Track ID recovers after brief occlusion (person partially hidden then reappears)
- [ ] New people entering the frame get a new unique ID
- [ ] IN counter increments when a person crosses the line in one direction
- [ ] OUT counter increments when a person crosses in the opposite direction
- [ ] The same crossing is never counted twice (no jitter double-counts)
- [ ] Trajectory trail appears behind each tracked person
- [ ] Visual flash triggers on every crossing event
- [ ] `R` key resets both counters to zero

If Track IDs are changing too frequently, increase `TRACK_BUFFER` in `config.py`. If the same crossing is counted multiple times, increase `LINE_CROSSING_TOLERANCE`.

---

## Next Steps

Week 3 adds three analytics layers on top of this tracking pipeline:

- **Heatmap**: accumulates foot traffic positions into a color overlay showing the most visited zones
- **Queue monitor**: counts persons inside a defined zone and triggers an alert above a threshold
- **Demographic estimation**: DeepFace estimates age range and gender per detected face, aggregated into statistics without storing any identity

The `TrackedPerson` class in `tracker.py` and the trajectory data in `PersonTracker.trajectories` are already structured to feed directly into the heatmap and zone analytics in Week 3 without modification.