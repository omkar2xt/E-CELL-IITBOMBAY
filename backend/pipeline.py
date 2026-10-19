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
from backend.alerts.evaluator import alert_evaluator
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

        # Video source and connection state
        self.source = be_config.VIDEO_SOURCE
        self.source_type = "unknown"
        self.connection_status = "stopped"
        self.error_message: Optional[str] = None
        self.is_demo = False
        self.cap: Optional[cv2.VideoCapture] = None

        # Load default zones on startup
        zone_analytics_engine.set_zones(ZoneAnalyticsEngine.default_zones())

    def _determine_source_type(self, source) -> str:
        if str(source).lower() in ("demo", "simulation"):
            return "demo"
        if isinstance(source, int):
            return "webcam"
        src_str = str(source).strip()
        if src_str.startswith(("rtsp://", "http://", "https://", "rtsps://")):
            return "stream"
        return "file"

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.connection_status = "connecting"
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            print(f"[Pipeline] Started background thread (source: {self.source})")

    def stop(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            print("[Pipeline] Stopped background thread")
        with self.lock:
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None
            self.connection_status = "stopped"

    def switch_source(self, new_source):
        """Switch video source dynamically with clean resource handoff."""
        if str(new_source).lower() in ("demo", "simulation"):
            resolved = "demo"
        else:
            resolved = be_config._resolve_video_source(new_source)
        print(f"[Pipeline] Switching source from {self.source} -> {resolved}")
        was_running = self.is_running
        if was_running:
            self.stop()
        with self.lock:
            self.source = resolved
            self.source_type = self._determine_source_type(resolved)
        if was_running:
            self.start()

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

    def _attempt_reconnect(self, source, retries: int = 5) -> Optional[cv2.VideoCapture]:
        """Attempt to reconnect to a camera/stream with bounded exponential delay."""
        delay = getattr(be_config, 'CAMERA_RECONNECT_DELAY_BASE', 1.0)
        max_delay = getattr(be_config, 'CAMERA_RECONNECT_DELAY_MAX', 10.0)

        for attempt in range(1, retries + 1):
            if not self.is_running:
                return None
            print(f"[Pipeline] Reconnecting to {source} (attempt {attempt}/{retries}) in {delay:.1f}s...")
            self.connection_status = "reconnecting"
            time.sleep(delay)

            try:
                cap = cv2.VideoCapture(source)
                if cap.isOpened():
                    print(f"[Pipeline] Successfully reconnected to {source} on attempt {attempt}")
                    self.connection_status = "connected"
                    self.error_message = None
                    return cap
                cap.release()
            except Exception as e:
                print(f"[Pipeline] Reconnection error on attempt {attempt}: {e}")

            delay = min(max_delay, delay * 2.0)

        return None

    def _run_loop(self):
        import analytics.config as an_config

        # Run demographics less frequently to save CPU on backend
        an_config.DEMO_ANALYSIS_INTERVAL = 30

        self.source_type = self._determine_source_type(self.source)

        if self.source_type == "demo":
            print("[Pipeline] Running in DEMO simulation mode (synthetically generated retail customer flow)")
            self.connection_status = "demo"
            self.is_demo = True
            self.error_message = None
            self._run_demo_loop()
            return

        # Check file existence if it's a file
        if self.source_type == "file" and not os.path.exists(str(self.source)):
            print(f"[Pipeline] Warning: Video file does not exist at {self.source}")
            print("[Pipeline] Running in DEMO simulation mode")
            self.connection_status = "demo"
            self.is_demo = True
            self.error_message = f"Video file not found: {self.source}"
            self._run_demo_loop()
            return

        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            print(f"[Pipeline] Could not open video source: {self.source} (type: {self.source_type})")
            # If camera or stream, attempt bounded reconnection before falling back
            if self.source_type in ("webcam", "stream"):
                cap = self._attempt_reconnect(self.source, retries=getattr(be_config, 'CAMERA_RECONNECT_MAX_RETRIES', 3))

            if cap is None or not cap.isOpened():
                print(f"[Pipeline] Source {self.source} unavailable. Falling back to DEMO mode.")
                self.connection_status = "demo"
                self.is_demo = True
                self.error_message = f"Video source unavailable: {self.source}"
                self._run_demo_loop()
                return

        with self.lock:
            self.cap = cap
            self.connection_status = "connected"
            self.is_demo = False
            self.error_message = None

        w, h, fps = get_dims(cap)
        self.frame_width = w
        self.frame_height = h
        line_start, line_end = build_line(w, h, an_config.LINE_ORIENTATION)

        tracker = PersonTracker()
        counter = LineCounter(line_start, line_end)
        heatmap = HeatmapGenerator(w, h)
        queue = QueueMonitor(w, h)

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
                if self.source_type == "file":
                    # Loop video file cleanly
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret_retry, frame = cap.read()
                    if not ret_retry:
                        # Reopen video file
                        cap.release()
                        cap = cv2.VideoCapture(self.source)
                        continue
                else:
                    # Live camera or stream dropped
                    print(f"[Pipeline] Connection dropped on {self.source_type}. Initiating reconnection...")
                    cap.release()
                    cap = self._attempt_reconnect(self.source, retries=getattr(be_config, 'CAMERA_RECONNECT_MAX_RETRIES', 5))
                    if cap is None or not cap.isOpened():
                        print(f"[Pipeline] Camera recovery failed. Falling back to DEMO mode.")
                        self.connection_status = "demo"
                        self.is_demo = True
                        self.error_message = f"Camera {self.source} disconnected."
                        self._run_demo_loop()
                        return
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

            # Phase 3: Zone analytics with explicit elapsed timestamp
            zone_analytics_engine.update(tracked, w, h, timestamp=now)

            if demo and demo.is_enabled:
                demo.update(frame, tracked)

            # Generate display frame
            frame_display = frame.copy()
            frame_display = heatmap.apply_to_frame(frame_display)
            frame_display = queue.draw_zone(frame_display)

            # Draw counting line
            color = (0, 60, 255) if counter.has_crossing_this_frame() else (0, 200, 255)
            cv2.line(frame_display, counter.line_start, counter.line_end, color, 2, cv2.LINE_AA)

            # Draw tracked person bounding boxes, labels, and tracking points
            for person in tracked:
                x1, y1, x2, y2 = [int(v) for v in person.bbox]
                cv2.rectangle(frame_display, (x1, y1), (x2, y2), (0, 255, 128), 2)
                label = f"ID:{person.track_id} ({person.confidence:.0%})"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                cv2.rectangle(frame_display, (x1, max(0, y1 - th - 6)), (x1 + tw + 4, max(th + 6, y1)), (0, 0, 0), -1)
                cv2.putText(frame_display, label, (x1 + 2, max(th + 2, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 128), 1, cv2.LINE_AA)
                bcx, bcy = person.bottom_center
                cv2.circle(frame_display, (bcx, bcy), 4, (0, 200, 255), -1)

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

                    zone_stats = zone_analytics_engine.get_zone_stats(current_time=now)
                    bottlenecks = zone_analytics_engine.get_bottleneck_summary()

                    self.latest_payload = {
                        "timestamp": now,
                        "frame_id": frame_id,
                        "count_in": counter.count_in,
                        "count_out": counter.count_out,
                        "occupancy": counter.current_occupancy,
                        "queue_count": queue.current_count,
                        "queue_alert": queue.is_alert,
                        "fps": round(fps_smoothed, 1),
                        "tracked_count": len(tracked),
                        "is_demo": False,
                        "source_type": self.source_type,
                        "connection_status": self.connection_status,
                        "demographics": {
                            "enabled": bool(demo and demo.is_enabled),
                            "sample_count": demo_results.get("sample_count", 0),
                            "gender_distribution": demo_results.get("gender_distribution", {}),
                            "age_distribution": demo_results.get("age_distribution", {}),
                        },
                        "zone_stats": zone_stats,
                        "bottlenecks": bottlenecks,
                    }

                    try:
                        alert_evaluator.evaluate_pipeline_state(
                            self.latest_payload,
                            frame=self.latest_frame,
                            source_mode="live" if self.source_type != "demo" else "demo"
                        )
                    except Exception:
                        pass


            # Cleanup old trajectories every 300 frames
            if frame_id % 300 == 0:
                active = {p.track_id for p in tracked}
                tracker.cleanup_old_tracks(active)
                counter.cleanup_old_tracks(active)

            # Throttle to approximate video FPS
            time.sleep(1.0 / max(30, fps))

        if cap is not None:
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
        base_in = 14
        base_out = 9

        # Canvas dimensions for simulation: 800 x 600
        sw, sh = 800, 600
        agents = [
            {"id": 1, "x": 80.0, "y": 480.0, "target": (450.0, 450.0), "speed": 3.0, "dwell_frames": 0},
            {"id": 2, "x": 450.0, "y": 450.0, "target": (580.0, 160.0), "speed": 2.5, "dwell_frames": 0},
            {"id": 3, "x": 580.0, "y": 160.0, "target": (380.0, 180.0), "speed": 2.0, "dwell_frames": 0},
            {"id": 4, "x": 380.0, "y": 180.0, "target": (200.0, 200.0), "speed": 2.5, "dwell_frames": 0},
            {"id": 5, "x": 200.0, "y": 200.0, "target": (80.0, 480.0), "speed": 2.0, "dwell_frames": 0},
            {"id": 6, "x": 220.0, "y": 220.0, "target": (450.0, 450.0), "speed": 2.2, "dwell_frames": 0},
        ]

        # Waypoints inside the 5 canonical zones
        waypoints = [
            (80.0, 480.0),   # Entrance: x in [0, 160], y in [360, 600]
            (450.0, 450.0),  # Grocery: x in [304, 600], y in [300, 600]
            (580.0, 160.0),  # Electronics: x in [440, 720], y in [60, 270]
            (380.0, 180.0),  # Promo Display: x in [320, 440], y in [90, 270]
            (200.0, 200.0),  # Checkout: x in [104, 296], y in [90, 300]
        ]

        heatmap = HeatmapGenerator(sw, sh)
        print("[Pipeline] Running in DEMO mode — simulated retail customer flow active")

        while self.is_running:
            frame_id += 1
            t = frame_id / 30.0

            # Update simulated agents positions with zone lingering
            sim_people = []
            checkout_count = 0
            for a in agents:
                tx, ty = a["target"]
                dx = tx - a["x"]
                dy = ty - a["y"]
                dist = math.hypot(dx, dy)

                if a["dwell_frames"] > 0:
                    # Lingering in current zone
                    a["dwell_frames"] -= 1
                    a["x"] += random.uniform(-0.4, 0.4)
                    a["y"] += random.uniform(-0.4, 0.4)
                elif dist < 20.0:
                    # Agent reached zone: linger for 30-90 frames (1-3 seconds)
                    a["dwell_frames"] = random.randint(30, 90)
                    choices = [w for w in waypoints if w != a["target"]]
                    a["target"] = random.choice(choices)
                else:
                    step = a["speed"]
                    a["x"] += (dx / dist) * step + random.uniform(-0.3, 0.3)
                    a["y"] += (dy / dist) * step + random.uniform(-0.3, 0.3)

                # Clamp within boundaries
                a["x"] = max(20.0, min(float(sw) - 20.0, a["x"]))
                a["y"] = max(20.0, min(float(sh) - 20.0, a["y"]))

                # Check if in checkout
                if 104.0 <= a["x"] <= 296.0 and 90.0 <= a["y"] <= 300.0:
                    checkout_count += 1

                sim_people.append(DemoTrackedPerson(a["id"], (int(a["x"]), int(a["y"]))))

            now = time.time()
            # Feed to zone analytics engine with timestamp
            zone_analytics_engine.update(sim_people, frame_width=sw, frame_height=sh, timestamp=now)

            # Accumulate heatmap positions
            heatmap.update([p.bottom_center for p in sim_people])

            if frame_id % 75 == 0:
                base_in += random.choice([0, 1])
            if frame_id % 95 == 0:
                base_out += random.choice([0, 1])

            # Queue count tied to checkout visitors with sinusoidal variation
            queue_count = max(checkout_count, int(1 + math.sin(t / 12) * 2.2 + random.uniform(0, 1.2)))

            # Generate visualization frame for /snapshot
            if frame_id % 2 == 0:
                demo_canvas = np.zeros((360, 640, 3), dtype=np.uint8)
                demo_canvas[:] = (20, 26, 35)  # sleek dark theme

                # Subtle floor grid
                for gx in range(0, 640, 40):
                    cv2.line(demo_canvas, (gx, 0), (gx, 360), (28, 36, 48), 1)
                for gy in range(0, 360, 40):
                    cv2.line(demo_canvas, (0, gy), (640, gy), (28, 36, 48), 1)

                # Draw zones with semi-transparent tint
                zones_list = zone_analytics_engine.get_zones()
                for z in zones_list:
                    pts = np.array([
                        [int(p[0] * 640), int(p[1] * 360)]
                        for p in z.polygon
                    ], np.int32).reshape((-1, 1, 2))
                    cv2.polylines(demo_canvas, [pts], True, z.color, 2, cv2.LINE_AA)
                    if len(pts) > 0:
                        cx, cy = pts[0][0]
                        cv2.putText(
                            demo_canvas, z.name,
                            (cx + 4, cy + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                            (255, 255, 255), 1, cv2.LINE_AA
                        )

                # Draw customer dots with glow and track labels
                for p in sim_people:
                    px = int((p.bottom_center[0] / sw) * 640)
                    py = int((p.bottom_center[1] / sh) * 360)
                    cv2.circle(demo_canvas, (px, py), 6, (0, 220, 255), -1, cv2.LINE_AA)
                    cv2.circle(demo_canvas, (px, py), 9, (0, 160, 200), 1, cv2.LINE_AA)
                    cv2.putText(
                        demo_canvas, f"#{p.track_id}",
                        (px + 8, py + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35,
                        (200, 240, 255), 1, cv2.LINE_AA
                    )

                # Status banner overlay
                cv2.rectangle(demo_canvas, (0, 0), (640, 28), (14, 19, 27), -1)
                cv2.putText(
                    demo_canvas, "StorePulse AI  [DEMO SIMULATION -- COHERENT RETAIL FLOW]",
                    (12, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                    (245, 180, 20), 1, cv2.LINE_AA
                )
                cv2.putText(
                    demo_canvas, f"Queue: {queue_count} {'(ALERT)' if queue_count >= 3 else ''}",
                    (520, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    (239, 68, 68) if queue_count >= 3 else (16, 185, 129), 1, cv2.LINE_AA
                )

                with self.lock:
                    self.latest_frame = demo_canvas
                    self.latest_heatmap_raw = heatmap._accumulator.copy()

            with self.lock:
                if frame_id % be_config.BROADCAST_INTERVAL == 0:
                    zone_stats = zone_analytics_engine.get_zone_stats(current_time=now)
                    bottlenecks = zone_analytics_engine.get_bottleneck_summary()
                    self.latest_payload = {
                        "timestamp": now,
                        "frame_id": frame_id,
                        "count_in": base_in,
                        "count_out": base_out,
                        "occupancy": max(0, base_in - base_out),
                        "queue_count": queue_count,
                        "queue_alert": queue_count >= 3,
                        "fps": 30.0,
                        "tracked_count": len(sim_people),
                        "is_demo": True,
                        "source_type": "demo",
                        "connection_status": "demo",
                        "demographics": {
                            "enabled": False,
                            "sample_count": 0,
                            "gender_distribution": {},
                            "age_distribution": {},
                        },
                        "zone_stats": zone_stats,
                        "bottlenecks": bottlenecks,
                    }

                    try:
                        alert_evaluator.evaluate_pipeline_state(
                            self.latest_payload,
                            frame=self.latest_frame,
                            source_mode="demo"
                        )
                    except Exception:
                        pass

            time.sleep(1.0 / 30.0)


pipeline_runner = AnalyticsPipeline()
