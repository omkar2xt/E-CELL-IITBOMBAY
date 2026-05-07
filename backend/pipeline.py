import cv2
import time
import threading
import sys
import os

# Add analytics and tracking to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'analytics')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tracking')))

from tracking.tracker import PersonTracker
from tracking.counter import LineCounter
from analytics.heatmap import HeatmapGenerator
from analytics.queue_monitor import QueueMonitor
from analytics.demographic import DemographicEstimator
from analytics.main import build_line, get_dims

import backend.settings as be_config
from backend.ws_manager import manager
import asyncio

class AnalyticsPipeline:
    def __init__(self):
        self.is_running = False
        self.thread = None
        self.latest_frame = None
        self.latest_heatmap = None
        self.lock = threading.Lock()
        
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

    def _run_loop(self):
        import analytics.config as an_config
        
        # Override analytics config if needed
        an_config.DEMO_ANALYSIS_INTERVAL = 30 # Run demo less frequently to save CPU on backend
        
        cap = cv2.VideoCapture(be_config.VIDEO_SOURCE)
        if not cap.isOpened():
            print(f"[Pipeline] Error: Could not open video {be_config.VIDEO_SOURCE}")
            return

        w, h, fps = get_dims(cap)
        line_start, line_end = build_line(w, h, an_config.LINE_ORIENTATION)
        
        tracker = PersonTracker()
        counter = LineCounter(line_start, line_end)
        heatmap = HeatmapGenerator(w, h)
        queue = QueueMonitor(w, h)
        demo = DemographicEstimator()
        
        # Demographic estimator sudah meng-handle inisialisasi OpenCV DNN di dalamnya.
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

            # Core pipeline
            tracked = tracker.update(frame)
            counter.update(tracked)
            
            positions = [p.bottom_center for p in tracked]
            heatmap.update(positions)
            queue.update(tracked)
            
            if demo.is_enabled:
                demo.update(frame, tracked)

            # Generate display frame (just heatmap and zones)
            frame_display = frame.copy()
            frame_display = heatmap.apply_to_frame(frame_display)
            frame_display = queue.draw_zone(frame_display)
            
            # Draw line
            color = (0, 60, 255) if counter.has_crossing_this_frame() else (0, 200, 255)
            cv2.line(frame_display, counter.line_start, counter.line_end, color, 2, cv2.LINE_AA)
            
            # Update snapshot and metrics
            with self.lock:
                self.latest_frame = frame_display
                
                # Update metrics periodically
                if frame_id % be_config.BROADCAST_INTERVAL == 0:
                    demo_results = demo.get_results() if demo.is_enabled else {}
                    
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
                            "enabled": demo.is_enabled,
                            "sample_count": demo_results.get("sample_count", 0),
                            "gender_distribution": demo_results.get("gender_distribution", {}),
                            "age_distribution": demo_results.get("age_distribution", {})
                        }
                    }

            # Small sleep to not consume 100% CPU and match rough video FPS
            time.sleep(1.0 / max(30, fps))

        cap.release()

pipeline_runner = AnalyticsPipeline()
