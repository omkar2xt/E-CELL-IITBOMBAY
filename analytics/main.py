# main.py - analytics module
# ============================================================
# StorePulse AI - Heatmap, Queue, and Demographic Analytics
#
# Usage:
#   python main.py --source video.mp4
#   python main.py --source 0
#   python main.py --source video.mp4 --save
#   python main.py --source video.mp4 --headless
#   python main.py --source video.mp4 --no-demo
#   python main.py --source video.mp4 --save-heatmap
# ============================================================

import cv2
import argparse
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tracking'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'detection'))

import config
from tracker import PersonTracker
from counter import LineCounter
from heatmap import HeatmapGenerator
from queue_monitor import QueueMonitor
from demographic import DemographicEstimator
from visualizer import AnalyticsVisualizer


def parse_args():
    parser = argparse.ArgumentParser(description="StorePulse AI - Analytics Pipeline")
    parser.add_argument("--source", default=str(config.VIDEO_SOURCE))
    parser.add_argument("--conf", type=float, default=config.TRACK_THRESH)
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--no-demo", action="store_true",
                        help="Disable demographic estimation (faster)")
    parser.add_argument("--save-heatmap", action="store_true",
                        help="Save a final heatmap snapshot on exit")
    parser.add_argument("--line-orientation", choices=["horizontal", "vertical"],
                        default=config.LINE_ORIENTATION)
    return parser.parse_args()


def open_source(source_str):
    try:
        source = int(source_str)
        print(f"[Main] Webcam: {source}")
    except ValueError:
        source = source_str
        print(f"[Main] Video: {source}")
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open: {source}")
        sys.exit(1)
    return cap


def get_dims(cap):
    w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    return w, h, fps


def build_line(w, h, orientation):
    if orientation == "horizontal":
        # Shift the vertical line position to the right area (80% of screen width)
        line_x = int(w * 0.8)
        
        # Line drawn from the middle of the screen (y=h*0.4) to the bottom of the screen (y=h) 
        return (line_x, int(h * 0.4)), (line_x, h)
    return (0, h // 2), (w, h // 2)


def setup_writer(cap, path):
    w, h, fps = get_dims(cap)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (w, h))
    print(f"[Main] Output: {path}")
    return writer


def print_controls():
    print("\n" + "="*52)
    print("  StorePulse AI - Analytics Pipeline")
    print("="*52)
    print("  [Q] / [ESC]  Quit")
    print("  [P]          Pause / Resume")
    print("  [H]          Toggle heatmap on/off")
    print("  [R]          Reset counter + heatmap")
    print("  [E]          Export current heatmap snapshot")
    print("  [S]          Screenshot")
    print("  [+] / [-]    Confidence threshold")
    print("="*52 + "\n")


def print_summary(counter, queue, demo):
    print("\n" + "="*42)
    print("  SESSION SUMMARY")
    print("="*42)
    print(f"  Total IN         : {counter.count_in}")
    print(f"  Total OUT        : {counter.count_out}")
    print(f"  Final Occupancy  : {counter.current_occupancy}")
    print(f"  Queue peak avg   : {queue.get_avg_count():.1f} persons")
    if demo.is_enabled:
        results = demo.get_results()
        total = results.get("sample_count", 0)
        if total > 0:
            print(f"\n  Demographics ({total} samples):")
            print(f"    Gender : {results['gender_distribution']}")
            print(f"    Age    : {results['age_distribution']}")
    print("="*42)


def main():
    args = parse_args()
    config.LINE_ORIENTATION = args.line_orientation
    config.TRACK_THRESH     = args.conf

    print_controls()

    # -- Init all components --
    tracker    = PersonTracker()
    cap        = open_source(args.source)
    w, h, fps  = get_dims(cap)

    line_start, line_end = build_line(w, h, args.line_orientation)
    counter    = LineCounter(line_start, line_end)
    heatmap    = HeatmapGenerator(w, h)
    queue      = QueueMonitor(w, h)
    demo       = DemographicEstimator()
    visualizer = AnalyticsVisualizer()

    if args.no_demo:
        demo._enabled = False
        print("[Main] Demographic estimation disabled.")

    writer       = setup_writer(cap, config.OUTPUT_PATH) if (args.save or args.headless) else None
    show_heatmap = True
    frame_count  = 0
    paused       = False
    screenshot_n = 0
    export_n     = 0

    try:
        while True:
            # -- Pause handler --
            if paused:
                key = cv2.waitKey(50) & 0xFF
                if key in [ord('p'), ord('P')]:
                    paused = False
                elif key in [ord('q'), ord('Q'), 27]:
                    break
                continue

            ret, frame = cap.read()
            if not ret:
                if cap.get(cv2.CAP_PROP_POS_FRAMES) > 0:
                    print("[Main] Video finished, looping...")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                break

            frame_count += 1

            # -- Core pipeline --

            # 1. Track everyone
            tracked = tracker.update(frame)

            # 2. Check crossings for IN/OUT counter
            counter.update(tracked)

            # 3. Update heatmap with all positions
            positions = [p.bottom_center for p in tracked]
            heatmap.update(positions)

            # 4. Update queue monitor
            queue.update(tracked)

            # 5. Update demographics (background thread, non-blocking)
            demo.update(frame, tracked)

            # -- Render --

            frame_display = frame.copy()

            # 6. Apply heatmap overlay first (bottom-most layer)
            if show_heatmap:
                frame_display = heatmap.apply_to_frame(frame_display)

            # 7. Draw cashier zone
            frame_display = queue.draw_zone(frame_display)

            # 8. Draw tracking overlay (box, ID, trajectory, line, panel)
            frame_display = visualizer.draw(
                frame_display,
                tracked,
                counter,
                tracker.trajectories,
                queue,
                demo,
            )

            # -- Output --
            if not args.headless:
                cv2.namedWindow(config.WINDOW_NAME, cv2.WINDOW_NORMAL)
                cv2.moveWindow(config.WINDOW_NAME, 100, 100)
                cv2.imshow(config.WINDOW_NAME, frame_display)
            else:
                if frame_count % 30 == 0:
                    alert = " [QUEUE ALERT!]" if queue.is_alert else ""
                    print(
                        f"[Main] Frame {frame_count:4d} | "
                        f"Tracked:{len(tracked):2d} | "
                        f"IN:{counter.count_in} OUT:{counter.count_out} | "
                        f"Queue:{queue.current_count}{alert}"
                    )

            if writer:
                writer.write(frame_display)

            # Cleanup old trajectories every 300 frames
            if frame_count % 300 == 0:
                active = {p.track_id for p in tracked}
                tracker.cleanup_old_tracks(active)

            # -- Keyboard --
            if args.headless:
                continue

            key = cv2.waitKey(1) & 0xFF

            if key in [ord('q'), ord('Q'), 27]:
                break
            elif key in [ord('p'), ord('P')]:
                paused = True
                print("[Main] Paused...")
            elif key in [ord('h'), ord('H')]:
                show_heatmap = not show_heatmap
                print(f"[Main] Heatmap: {'ON' if show_heatmap else 'OFF'}")
            elif key in [ord('r'), ord('R')]:
                counter.reset_counts()
                heatmap.reset()
                print("[Main] Reset: counter + heatmap.")
            elif key in [ord('e'), ord('E')]:
                export_n += 1
                fname = f"heatmap_export_{export_n:03d}.jpg"
                overlay = heatmap.get_overlay()
                cv2.imwrite(fname, overlay)
                print(f"[Main] Heatmap saved: {fname}")
            elif key in [ord('s'), ord('S')]:
                screenshot_n += 1
                fname = f"screenshot_w3_{screenshot_n:03d}.jpg"
                cv2.imwrite(fname, frame_display)
                print(f"[Main] Screenshot: {fname}")
            elif key == ord('+'):
                config.TRACK_THRESH = min(0.95, config.TRACK_THRESH + 0.05)
                print(f"[Main] Confidence: {config.TRACK_THRESH:.2f}")
            elif key == ord('-'):
                config.TRACK_THRESH = max(0.1, config.TRACK_THRESH - 0.05)
                print(f"[Main] Confidence: {config.TRACK_THRESH:.2f}")

    except KeyboardInterrupt:
        print("\n[Main] Stopped.")

    finally:
        if args.save_heatmap:
            overlay = heatmap.get_overlay()
            hm_path = "heatmap_final.jpg"
            cv2.imwrite(hm_path, overlay)
            print(f"[Main] Final heatmap: {hm_path}")

        print_summary(counter, queue, demo)
        cap.release()
        if writer:
            writer.release()
            print(f"[Main] Video: {config.OUTPUT_PATH}")
        cv2.destroyAllWindows()
        print("[Main] Finished.")


if __name__ == "__main__":
    main()