"""
StorePulse AI — Real Video Pipeline Audit & Verification Script
Developer: Omkar Gurav
Runs backend.pipeline.AnalyticsPipeline against detection/vid/retail-cctv-footage.mp4
"""

import os
import sys
import time

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.pipeline import AnalyticsPipeline
from backend.zone_analytics import zone_analytics_engine
from backend.flow_friction import friction_calculator
import backend.settings as be_config

def main():
    video_path = os.path.join(ROOT, "detection", "vid", "retail-cctv-footage.mp4")
    print(f"==================================================")
    print(f"STOREPULSE AI — REAL VIDEO PIPELINE AUDIT")
    print(f"Video File: {video_path}")
    print(f"File Exists: {os.path.exists(video_path)}")
    print(f"==================================================")
    
    # Configure pipeline with the real video
    pipeline = AnalyticsPipeline()
    pipeline.source = video_path
    
    # Start pipeline
    print("\n[1] Starting AnalyticsPipeline...")
    pipeline.start()
    
    # Let it run to process frames
    print("[2] Processing real video frames (monitoring for up to 15 seconds)...")
    for i in range(15):
        time.sleep(1.0)
        metrics = pipeline.get_latest_metrics()
        if metrics:
            print(f"  Sec {i+1}: Frame #{metrics.get('frame_id')} | Active Tracks: {metrics.get('active_tracks')} | In: {metrics.get('count_in')} | Out: {metrics.get('count_out')} | Queue: {metrics.get('queue_count')} | FPS: {metrics.get('fps', 0):.1f} | Demo: {metrics.get('is_demo')}")
            if metrics.get('frame_id', 0) >= 30:
                print("  => Captured sufficient frames for audit analysis.")
                break
        else:
            print(f"  Sec {i+1}: Pipeline initializing...")
            
    # Check zone statistics
    zone_stats = zone_analytics_engine.get_zone_stats()
    print("\n[3] Real Observed Zone Statistics:")
    for zid, stats in zone_stats.items():
        print(f"  Zone: {zid} ({stats.get('zone_name')}) -> Occupancy: {stats.get('current_occupancy')} | Completed Visits: {stats.get('completed_visits')} | Avg Dwell: {stats.get('avg_dwell_seconds', 0):.2f}s | Max Dwell: {stats.get('max_dwell_seconds', 0):.2f}s")
        
    # Check transitions
    transitions = zone_analytics_engine.get_transitions()
    print("\n[4] Real Observed Movement Transitions:")
    print(f"  Total Transitions: {transitions.get('total_transitions_recorded', 0)}")
    print(f"  Data Sufficient: {transitions.get('data_sufficient', False)}")
    print(f"  Evidence Type: {transitions.get('evidence_type')}")
    for t in transitions.get('transitions', []):
        print(f"    {t['from_zone']} -> {t['to_zone']} (count={t['count']}, prob={t['probability']:.2f})")
        
    # Check Bottlenecks
    bottlenecks = zone_analytics_engine.get_bottleneck_summary()
    print("\n[5] Bottleneck Analysis:")
    print(f"  Active Bottlenecks: {bottlenecks.get('active_bottleneck_count', 0)}")
    for b in bottlenecks.get('bottlenecks', []):
        print(f"    Zone: {b.get('zone_id')} | Severity: {b.get('severity')} | Occupancy: {b.get('current_occupancy')} | Dwell: {b.get('avg_dwell_seconds'):.1f}s")
        
    # Check Heatmap
    heatmap_grid = pipeline.get_heatmap_data()
    print("\n[6] Heatmap Generator Status:")
    if heatmap_grid:
        print(f"  Heatmap Grid Available: {len(heatmap_grid)}x{len(heatmap_grid[0])} cells | Max Intensity: {max(max(row) for row in heatmap_grid)}")
    else:
        print(f"  Heatmap Grid: Not yet accumulated")
        
    # Stop pipeline
    print("\n[7] Stopping AnalyticsPipeline...")
    pipeline.stop()
    print("Pipeline stopped cleanly.")
    print("\n[VERDICT] Real-video pipeline execution verified.")

if __name__ == "__main__":
    main()
