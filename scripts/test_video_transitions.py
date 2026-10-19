"""
Test Video Transitions with retail-cctv-footage.mp4
"""
import cv2
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tracking.tracker import PersonTracker
from backend.zone_analytics import zone_analytics_engine, ZoneAnalyticsEngine

def test_video():
    zone_analytics_engine.reset()
    zone_analytics_engine.set_zones(ZoneAnalyticsEngine.default_zones())

    video_path = "detection/vid/retail-cctv-footage.mp4"
    cap = cv2.VideoCapture(video_path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Video: {w}x{h}, {total_frames} frames")

    tracker = PersonTracker()
    frame_idx = 0
    trajectories = {}

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1
        t = frame_idx / 30.0
        tracked = tracker.update(frame)
        zone_analytics_engine.update(tracked, w, h, timestamp=t)
        for p in tracked:
            tid = p.track_id
            if tid not in trajectories:
                trajectories[tid] = []
            trajectories[tid].append((p.bottom_center[0] / w, p.bottom_center[1] / h))

    cap.release()
    print(f"Processed {frame_idx} frames. Total unique tracks: {len(trajectories)}")
    for tid, pts in trajectories.items():
        print(f"  Track {tid}: {len(pts)} frames, start=({pts[0][0]:.2f}, {pts[0][1]:.2f}), end=({pts[-1][0]:.2f}, {pts[-1][1]:.2f})")

    stats = zone_analytics_engine.get_zone_stats()
    for s in stats:
        print(f"Zone {s['zone_name']}: entries={s['total_entries']}, completed={s['completed_visits']}, active={s['current_occupancy']}")

    trans = zone_analytics_engine.get_transitions()
    print("Transitions:", trans["transitions"])
    print("Total transitions:", trans["total_transitions"])

if __name__ == "__main__":
    test_video()
