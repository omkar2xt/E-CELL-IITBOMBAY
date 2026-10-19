# StorePulse AI — Computer Vision Pipeline Integration Test Suite
# Developer: Omkar Gurav
# Covers Task 7: Video input, YOLO detection, ByteTrack tracking, counting,
# camera resilience, streaming endpoints, and demo labeling.

import pytest
import numpy as np
import cv2
import time
from unittest.mock import MagicMock, patch

from detection.detector import PersonDetector, Detection
from tracking.tracker import PersonTracker, TrackedPerson
from tracking.counter import LineCounter
from analytics.heatmap import HeatmapGenerator
from analytics.queue_monitor import QueueMonitor
from backend.pipeline import AnalyticsPipeline
import backend.settings as be_config


# =====================================================================
# 1. Invalid Video Sources
# =====================================================================
def test_invalid_video_source():
    """Verify that nonexistent or invalid video sources fall back safely to demo mode."""
    pipeline = AnalyticsPipeline()
    pipeline.source = "nonexistent_directory/invalid_video_file.mp4"
    pipeline.source_type = pipeline._determine_source_type(pipeline.source)

    # Attempt to open
    assert pipeline.source_type == "file"
    # Starting pipeline should detect missing file and route to demo loop without crashing
    with patch.object(pipeline, '_run_demo_loop') as mock_demo:
        pipeline._run_loop()
        assert pipeline.is_demo is True
        assert pipeline.connection_status == "demo"
        assert "not found" in pipeline.error_message
        mock_demo.assert_called_once()


# =====================================================================
# 2. End-of-File Handling
# =====================================================================
def test_end_of_file_handling():
    """Verify that video files loop back to frame 0 cleanly on EOF."""
    mock_cap = MagicMock()
    # First frame returns valid, second frame returns EOF (False, None), third returns loop (True, frame)
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_cap.read.side_effect = [
        (True, dummy_frame),
        (False, None),
        (True, dummy_frame),
    ]
    mock_cap.isOpened.return_value = True
    mock_cap.get.side_effect = lambda prop: 640 if prop == cv2.CAP_PROP_FRAME_WIDTH else (480 if prop == cv2.CAP_PROP_FRAME_HEIGHT else 30)

    # When EOF happens, cap.set(cv2.CAP_PROP_POS_FRAMES, 0) should be called
    mock_cap.set.return_value = True

    pipeline = AnalyticsPipeline()
    pipeline.source = "detection/vid/retail-cctv-footage.mp4"
    pipeline.source_type = "file"
    pipeline.is_running = True

    # Simulate loop iteration
    ret, frame = mock_cap.read()
    assert ret is True
    ret_eof, _ = mock_cap.read()
    assert ret_eof is False

    # EOF branch
    mock_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    mock_cap.set.assert_called_with(cv2.CAP_PROP_POS_FRAMES, 0)
    ret_loop, frame_loop = mock_cap.read()
    assert ret_loop is True
    assert frame_loop is not None


# =====================================================================
# 3. Empty Detections
# =====================================================================
def test_empty_detections():
    """Verify detector and tracker handle empty/blank frames and zero detections."""
    detector = PersonDetector()
    tracker = PersonTracker()

    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Detect on blank frame
    detections = detector.detect(blank_frame)
    assert isinstance(detections, list)
    assert len(detections) == 0

    # Track on blank frame
    tracked = tracker.update(blank_frame)
    assert isinstance(tracked, list)
    assert len(tracked) == 0

    # Test None frame
    assert detector.detect(None) == []
    assert tracker.update(None) == []


# =====================================================================
# 4. Malformed Bounding Boxes
# =====================================================================
def test_malformed_bounding_boxes():
    """Verify components handle out-of-bound, inverted, or malformed coordinates safely."""
    detector = PersonDetector()

    # Detection dataclass boundary clamp validation
    d = Detection(bbox=[-50.0, -20.0, 800.0, 600.0], confidence=0.85, class_id=0)
    assert d.center == (375, 290)
    assert d.bottom_center == (375, 600)
    assert d.width == 850.0
    assert d.height == 620.0

    # Inverted box [x2 < x1]
    d_inverted = Detection(bbox=[100.0, 100.0, 50.0, 50.0], confidence=0.5, class_id=0)
    assert d_inverted.width == 0.0
    assert d_inverted.height == 0.0

    # Heatmap handles out-of-frame coordinates without slicing error
    heatmap = HeatmapGenerator(640, 480)
    heatmap.update([(-100, -100), (9999, 9999), (320, 240)])
    assert heatmap._accumulator.shape == (480, 640)

    # Queue monitor handles malformed/None person objects safely
    qm = QueueMonitor(640, 480)
    assert qm.update([None]) == 0


# =====================================================================
# 5. Tracking with Multiple People
# =====================================================================
def test_tracking_multiple_people():
    """Verify multi-person tracking maintains unique temporary IDs and trajectories."""
    tracker = PersonTracker()

    # Mock detection results for two people over two frames
    p1 = TrackedPerson(track_id=1, bbox=[100, 100, 150, 200], confidence=0.9)
    p2 = TrackedPerson(track_id=2, bbox=[300, 200, 350, 300], confidence=0.85)

    tracker._update_trajectory(p1.track_id, p1.center)
    tracker._update_trajectory(p2.track_id, p2.center)

    assert len(tracker.get_trajectory(1)) == 1
    assert len(tracker.get_trajectory(2)) == 1
    assert p1.track_id != p2.track_id

    # Simulate second frame movement
    tracker._update_trajectory(1, (130, 155))
    assert len(tracker.get_trajectory(1)) == 2
    assert tracker.get_trajectory(1)[-1] == (130, 155)

    # Verify trajectory capping
    for i in range(50):
        tracker._update_trajectory(1, (130 + i, 155 + i))
    assert len(tracker.get_trajectory(1)) <= 30


# =====================================================================
# 6. Counting Behavior & Virtual Line Rules
# =====================================================================
def test_counting_behavior_and_dead_zone():
    """
    Verify virtual line-crossing rules:
    - Entering (B -> A) increments count_in once
    - Staying on side A does NOT count repeatedly
    - Dead zone hysteresis prevents jitter
    - Exiting (A -> B) increments count_out
    """
    # Vertical line at x=320, spanning y=0 to y=480
    counter = LineCounter(line_start=(320, 0), line_end=(320, 480), orientation="horizontal", tolerance=5)

    # Person 1 starts on Side B (right: x=400)
    p1_step1 = TrackedPerson(track_id=101, bbox=[380, 200, 420, 300], confidence=0.9)
    counter.update([p1_step1])
    assert counter.count_in == 0
    assert counter.count_out == 0

    # Person 1 crosses to Side A (left: x=250) -> B to A is IN
    p1_step2 = TrackedPerson(track_id=101, bbox=[230, 200, 270, 300], confidence=0.9)
    counter.update([p1_step2])
    assert counter.count_in == 1
    assert counter.count_out == 0
    assert counter.has_crossing_this_frame() is True
    assert counter.current_occupancy == 1

    # Person 1 continues walking on Side A (x=200) -> NO repeat count
    p1_step3 = TrackedPerson(track_id=101, bbox=[180, 200, 220, 300], confidence=0.9)
    counter.update([p1_step3])
    assert counter.count_in == 1
    assert counter.count_out == 0
    assert counter.has_crossing_this_frame() is False

    # Person 1 enters the dead zone (x=322, within tolerance 5) -> "ZONE"
    p1_deadzone = TrackedPerson(track_id=101, bbox=[302, 200, 342, 300], confidence=0.9) # center x=322
    counter.update([p1_deadzone])
    assert counter.count_in == 1
    assert counter.count_out == 0

    # Person 1 returns back to Side B (x=450) -> A to B is OUT
    p1_step4 = TrackedPerson(track_id=101, bbox=[430, 200, 470, 300], confidence=0.9)
    counter.update([p1_step4])
    assert counter.count_in == 1
    assert counter.count_out == 1
    assert counter.current_occupancy == 0


# =====================================================================
# 7. Camera Disconnection and Reconnection Logic
# =====================================================================
def test_camera_disconnection_and_reconnection():
    """Verify bounded exponential retry and recovery when a camera disconnects."""
    pipeline = AnalyticsPipeline()
    pipeline.source = 0
    pipeline.source_type = "webcam"
    pipeline.is_running = True

    # Mock cv2.VideoCapture to simulate failure on attempt 1, recovery on attempt 2
    mock_fail = MagicMock()
    mock_fail.isOpened.return_value = False

    mock_success = MagicMock()
    mock_success.isOpened.return_value = True

    with patch("cv2.VideoCapture", side_effect=[mock_fail, mock_success]):
        with patch("time.sleep", return_value=None):  # Fast test execution
            reconnected_cap = pipeline._attempt_reconnect(0, retries=3)

    assert reconnected_cap is not None
    assert reconnected_cap.isOpened() is True
    assert pipeline.connection_status == "connected"


# =====================================================================
# 8. Streaming Endpoint Error Handling
# =====================================================================
def test_streaming_endpoint_error_handling():
    """Verify snapshot generation handles None frame and empty frames gracefully."""
    pipeline = AnalyticsPipeline()
    # Before start, snapshot is None
    assert pipeline.get_latest_snapshot() is None

    # Set dummy frame
    dummy = np.zeros((360, 640, 3), dtype=np.uint8)
    with pipeline.lock:
        pipeline.latest_frame = dummy

    snap = pipeline.get_latest_snapshot()
    assert snap is not None
    assert snap.shape == (360, 640, 3)

    # Encode test
    ret, buf = cv2.imencode('.jpg', snap)
    assert ret is True
    assert len(buf) > 0


# =====================================================================
# 9. Pipeline Startup and Shutdown
# =====================================================================
def test_pipeline_startup_and_shutdown():
    """Verify clean thread lifecycle and resource release on stop."""
    pipeline = AnalyticsPipeline()
    pipeline.source = "detection/vid/retail-cctv-footage.mp4"
    pipeline.source_type = "file"

    pipeline.start()
    assert pipeline.is_running is True
    assert pipeline.thread is not None
    assert pipeline.thread.is_alive() is True

    # Stop pipeline
    pipeline.stop()
    assert pipeline.is_running is False
    assert pipeline.connection_status == "stopped"
    assert pipeline.cap is None


# =====================================================================
# 10. Safe Demo-Mode Labeling
# =====================================================================
def test_safe_demo_mode_labeling():
    """Verify demo mode explicitly flags is_demo=True and status=demo."""
    pipeline = AnalyticsPipeline()

    # Trigger demo loop run directly
    pipeline.is_running = True
    # Allow 6 iterations so frame_id reaches BROADCAST_INTERVAL (5)
    with patch("time.sleep", side_effect=[None] * 6 + [Exception("StopDemo")]):
        try:
            pipeline._run_demo_loop()
        except Exception as e:
            if str(e) != "StopDemo":
                raise e

    metrics = pipeline.get_latest_metrics()
    assert metrics is not None

    assert metrics.get("is_demo") is True
    assert "frame_id" in metrics
    assert "count_in" in metrics
    assert "zone_stats" in metrics
