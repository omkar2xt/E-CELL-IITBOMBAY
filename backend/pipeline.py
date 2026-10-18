# StorePulse AI — Computer Vision Analytics Pipeline
# Developer: Omkar Gurav

import cv2
import time
import threading
import sys
import os
import numpy as np
from typing import Tuple, Dict, List, Optional

# Add analytics and tracking to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'analytics')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tracking')))

from tracking.tracker import PersonTracker
from tracking.counter import LineCounter
from analytics.heatmap import HeatmapGenerator
from analytics.queue_monitor import QueueMonitor
from analytics.main import build_line, get_dims

import backend.settings as be_config
from backend.ws_manager import manager
from backend.zone_analytics import zone_analytics_engine, ZoneAnalyticsEngine
import asyncio


class AnalyticsPipeline:
    def __init__(self):
        self.is_running = False
        self.thread = None
        self.latest_frame = None
        self.latest_heatmap_raw = None  # raw float32 accumulator snapshot
        self.lock = threading.Lock()
        self.frame_width = 0
        self.frame_height = 0

        # Load default zones on startup
        zone_analytics_engine.set_zones(ZoneAnalyticsEngine.default_zones())

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            print("[Pipeline] Started background thread")

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            print("[Pipeline] Stopped background thread")

    def get_latest_snapshot(self):
        with self.lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy()

    def get_latest_metrics(self):
        with self.lock:
            if hasattr(self, 'latest_payload'):
                return self.latest_payload
            return None

    def clear_latest_metrics(self):
        with self.lock:
            if hasattr(self, 'latest_payload'):
                delattr(self, 'latest_payload')

    def get_heatmap_data(self):
        """Return heatmap as a small grid of values for frontend rendering."""
        with self.lock:
            if self.latest_heatmap_raw is None:
                return None
            raw = self.latest_heatmap_raw
        # Downsample to 64x64 for API transfer
        try:
            small = cv2.resize(raw, (64, 64))
            if small.max() > 0:
                normalized = cv2.normalize(small, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            else:
                normalized = small.astype(np.uint8)
            return normalized.tolist()
        except Exception:
            return None

    def _run_loop(self):
        import analytics.config as an_config

        # Run demographics less frequently to save CPU on backend
        an_config.DEMO_ANALYSIS_INTERVAL = 30

        cap = cv2.VideoCapture(be_config.VIDEO_SOURCE)
        if not cap.isOpened():
            print(f"[Pipeline] Error: Could not open video {be_config.VIDEO_SOURCE}")
            print("[Pipeline] Running in demo mode (no video)")
            self._run_demo_loop()
            return

        w, h, fps = get_dims(cap)
        self.frame_width = w
        self.frame_height = h
        line_start, line_end = build_line(w, h, an_config.LINE_ORIENTATION)

        tracker = PersonTracker()
        counter = LineCounter(line_start, line_end)
        heatmap = HeatmapGenerator(w, h)
        queue = QueueMonitor(w, h)

        # Demographic estimation — disabled by default (privacy)
        demo = None
        if be_config.DEMOGRAPHICS_ENABLED:
            try:
                from analytics.demographic import DemographicEstimator
                demo = DemographicEstimator()
            except Exception as e:
                print(f"[Pipeline] Demographics disabled: {e}")

        frame_id = 0
        prev_time = time.time()
        fps_smoothed = 0.0

        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                # Loop video
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            frame_id += 1

            # FPS calculation
            now = time.time()
            dt = now - prev_time
            prev_time = now
            if dt > 0:
                fps_smoothed = 0.9 * fps_smoothed + 0.1 * (1.0 / dt)

            # Core CV pipeline
            tracked = tracker.update(frame)
            counter.update(tracked)

            positions = [p.bottom_center for p in tracked]
            heatmap.update(positions)
            queue.update(tracked)

            # Phase 3: Zone analytics
            zone_analytics_engine.update(tracked, w, h)

            if demo and demo.is_enabled:
                demo.update(frame, tracked)

            # Generate display frame
            frame_display = frame.copy()
            frame_display = heatmap.apply_to_frame(frame_display)
            frame_display = queue.draw_zone(frame_display)

            # Draw counting line
            color = (0, 60, 255) if counter.has_crossing_this_frame() else (0, 200, 255)
            cv2.line(frame_display, counter.line_start, counter.line_end, color, 2, cv2.LINE_AA)

            # StorePulse AI branding overlay
            cv2.putText(
                frame_display, "StorePulse AI",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (255, 200, 0), 2, cv2.LINE_AA
            )

            # Update snapshot and metrics
            with self.lock:
                self.latest_frame = frame_display
                self.latest_heatmap_raw = heatmap._accumulator.copy()

                if frame_id % be_config.BROADCAST_INTERVAL == 0:
                    demo_results = {}
                    if demo and demo.is_enabled:
                        demo_results = demo.get_results()

                    zone_stats = zone_analytics_engine.get_zone_stats()

                    self.latest_payload = {
                        "timestamp": time.time(),
                        "frame_id": frame_id,
                        "count_in": counter.count_in,
                        "count_out": counter.count_out,
                        "occupancy": counter.current_occupancy,
                        "queue_count": queue.current_count,
                        "queue_alert": queue.is_alert,
                        "fps": round(fps_smoothed, 1),
                        "tracked_count": len(tracked),
                        "demographics": {
                            "enabled": bool(demo and demo.is_enabled),
                            "sample_count": demo_results.get("sample_count", 0),
                            "gender_distribution": demo_results.get("gender_distribution", {}),
                            "age_distribution": demo_results.get("age_distribution", {}),
                        },
                        "zone_stats": zone_stats,
                    }

            # Cleanup old trajectories every 300 frames
            if frame_id % 300 == 0:
                active = {p.track_id for p in tracked}
                tracker.cleanup_old_tracks(active)

            # Throttle to approximate video FPS
            time.sleep(1.0 / max(30, fps))

        cap.release()

    def _run_demo_loop(self):
        """
        Demo mode: emit synthetic metrics and update zone analytics when no video is available.
        Clearly labeled as DEMO data throughout.
        """
        import random
        import math

        class DemoTrackedPerson:
            def __init__(self, track_id: int, bottom_center: Tuple[int, int]):
                self.track_id = track_id
                self.bottom_center = bottom_center

        frame_id = 0
        base_in = 12
        base_out = 8

        # Simulated store agents with wander targets
        # Canvas dimensions for simulation: 800 x 600
        sw, sh = 800, 600
        agents = [
            {"id": 1, "x": 100.0, "y": 480.0, "target": (450.0, 450.0), "speed": 2.5},
            {"id": 2, "x": 420.0, "y": 420.0, "target": (500.0, 480.0), "speed": 1.8},
            {"id": 3, "x": 620.0, "y": 200.0, "target": (680.0, 150.0), "speed": 1.5},
            {"id": 4, "x": 660.0, "y": 420.0, "target": (720.0, 440.0), "speed": 2.0},
            {"id": 5, "x": 220.0, "y": 200.0, "target": (210.0, 220.0), "speed": 1.0},
            {"id": 6, "x": 240.0, "y": 220.0, "target": (230.0, 190.0), "speed": 0.8},
        ]

        # Waypoints for department wandering
        waypoints = [
            (100.0, 480.0),  # Entrance
            (450.0, 450.0),  # Grocery
            (620.0, 200.0),  # Electronics
            (660.0, 420.0),  # Promo
            (220.0, 200.0),  # Checkout
        ]

        print("[Pipeline] Running in DEMO mode — simulated retail customer flow active")

        while self.is_running:
            frame_id += 1
            t = frame_id / 30.0

            # Update simulated agents positions
            sim_people = []
            for a in agents:
                tx, ty = a["target"]
                dx = tx - a["x"]
                dy = ty - a["y"]
                dist = math.hypot(dx, dy)
                if dist < 15.0:
                    # Pick new target waypoint
                    a["target"] = random.choice(waypoints)
                else:
                    step = a["speed"]
                    a["x"] += (dx / dist) * step + random.uniform(-0.5, 0.5)
                    a["y"] += (dy / dist) * step + random.uniform(-0.5, 0.5)

                sim_people.append(DemoTrackedPerson(a["id"], (int(a["x"]), int(a["y"]))))

            # Feed to zone analytics engine
            zone_analytics_engine.update(sim_people, frame_width=sw, frame_height=sh)

            if frame_id % 60 == 0:
                base_in += random.choice([0, 1])
            if frame_id % 90 == 0:
                base_out += random.choice([0, 1])

            queue_count = max(0, int(1 + math.sin(t / 15) * 2 + random.gauss(0, 0.5)))

            # Generate lightweight visualization frame for /snapshot
            if frame_id % 2 == 0:
                demo_canvas = np.zeros((360, 640, 3), dtype=np.uint8)
                demo_canvas[:] = (22, 28, 36)  # dark background

                # Draw grid lines
                for gx in range(0, 640, 40):
                    cv2.line(demo_canvas, (gx, 0), (gx, 360), (30, 38, 48), 1)
                for gy in range(0, 360, 40):
                    cv2.line(demo_canvas, (0, gy), (640, gy), (30, 38, 48), 1)

                # Draw zones
                for z in zone_analytics_engine.get_zones():
                    pts = np.array([
                        [int(p[0] * 640), int(p[1] * 360)]
                        for p in z.polygon
                    ], np.int32)
                    pts = pts.reshape((-1, 1, 2))
                    cv2.polylines(demo_canvas, [pts], True, z.color, 1, cv2.LINE_AA)
                    if len(pts) > 0:
                        cx, cy = pts[0][0]
                        cv2.putText(
                            demo_canvas, z.name,
                            (cx + 4, cy + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.35,
                            z.color, 1, cv2.LINE_AA
                        )

                # Draw people dots
                for p in sim_people:
                    px = int((p.bottom_center[0] / sw) * 640)
                    py = int((p.bottom_center[1] / sh) * 360)
                    cv2.circle(demo_canvas, (px, py), 5, (0, 220, 255), -1, cv2.LINE_AA)
                    cv2.circle(demo_canvas, (px, py), 7, (0, 180, 220), 1, cv2.LINE_AA)

                # Branding header
                cv2.putText(
                    demo_canvas, "StorePulse AI [SIMULATION MODE]",
                    (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (255, 200, 0), 1, cv2.LINE_AA
                )

                with self.lock:
                    self.latest_frame = demo_canvas

            with self.lock:
                if frame_id % be_config.BROADCAST_INTERVAL == 0:
                    zone_stats = zone_analytics_engine.get_zone_stats()
                    self.latest_payload = {
                        "timestamp": time.time(),
                        "frame_id": frame_id,
                        "count_in": base_in,
                        "count_out": base_out,
                        "occupancy": max(0, base_in - base_out),
                        "queue_count": queue_count,
                        "queue_alert": queue_count >= 3,
                        "fps": 30.0,
                        "tracked_count": len(sim_people),
                        "is_demo": True,
                        "demographics": {
                            "enabled": False,
                            "sample_count": 0,
                            "gender_distribution": {},
                            "age_distribution": {},
                        },
                        "zone_stats": zone_stats,
                    }

            time.sleep(1.0 / 30.0)


pipeline_runner = AnalyticsPipeline()
