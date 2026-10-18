# main.py
# ============================================================
# Entry point. Run: python main.py
#
# To use a video file:
#   python main.py --source path/to/video.mp4
#
# To use a webcam:
#   python main.py --source 0
#
# To save output:
#   python main.py --source video.mp4 --save
# ============================================================

import cv2
import argparse
import sys
import config
from detector import PersonDetector
from visualizer import Visualizer


def parse_args():
    parser = argparse.ArgumentParser(
        description="StorePulse AI - Person Detection Pipeline"
    )
    parser.add_argument(
        "--source",
        default=str(config.VIDEO_SOURCE),
        help="Path to video file, or number for webcam (0, 1, ...)"
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=config.CONFIDENCE_THRESHOLD,
        help="Confidence threshold (default: 0.4)"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save output video to file"
    )
    return parser.parse_args()


def open_video_source(source_str: str) -> cv2.VideoCapture:
    """
    Open video from file or webcam.
    Source can be:
    - "0" or "1" -> webcam index
    - "path/to/file.mp4" -> video file
    """
    # Try to parse as integer (webcam index)
    try:
        source = int(source_str)
        print(f"[Main] Opening webcam index: {source}")
    except ValueError:
        source = source_str
        print(f"[Main] Opening video file: {source}")

    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"[ERROR] Could not open source: {source}")
        print("Please check:")
        print("  - Video path is correct")
        print("  - Webcam is available (try index 0 or 1)")
        sys.exit(1)

    return cap


def setup_video_writer(cap: cv2.VideoCapture, output_path: str):
    """Setup VideoWriter if --save is active."""
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    print(f"[Main] Output will be saved to: {output_path}")
    return writer


def print_controls():
    print("\n" + "="*50)
    print("  StorePulse AI - Person Detection Pipeline")
    print("="*50)
    print("  Keyboard controls:")
    print("  [Q] or [ESC] -> Quit")
    print("  [P]          -> Pause / Resume")
    print("  [+] / [-]    -> Increase/decrease confidence threshold")
    print("  [S]          -> Screenshot current frame")
    print("="*50 + "\n")


def main():
    args = parse_args()

    # Override config from command line arguments
    config.CONFIDENCE_THRESHOLD = args.conf
    config.SAVE_OUTPUT = args.save

    print_controls()

    # -- Initialize components --
    detector = PersonDetector()
    visualizer = Visualizer()
    cap = open_video_source(args.source)
    writer = setup_video_writer(cap, config.OUTPUT_PATH) if args.save else None

    # Video info
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_source = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[Main] Resolution: {width}x{height}, Source FPS: {fps_source:.1f}")
    if total_frames > 0:
        duration = total_frames / fps_source if fps_source > 0 else 0
        print(f"[Main] Total frames: {total_frames} ({duration:.1f} seconds)\n")

    # -- Main loop --
    paused = False
    frame_count = 0
    screenshot_count = 0

    try:
        while True:
            # Handle pause
            if paused:
                key = cv2.waitKey(50) & 0xFF
                if key in [ord('p'), ord('P')]:
                    paused = False
                    print("[Main] Resumed")
                elif key in [ord('q'), ord('Q'), 27]:
                    break
                continue

            # Read next frame
            ret, frame = cap.read()

            if not ret:
                # Video file ended -> loop from start (if file), or stop (webcam)
                if isinstance(cap.get(cv2.CAP_PROP_POS_FRAMES), float):
                    print("[Main] Video finished. Looping from start...")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    print("[Main] Stream ended.")
                    break

            frame_count += 1

            # -- Core pipeline --

            # 1. Detect everyone in this frame
            detections = detector.detect(frame)

            # 2. Draw results on frame
            frame_display = visualizer.draw(frame, detections)

            # 3. Display
            cv2.namedWindow(config.WINDOW_NAME, cv2.WINDOW_NORMAL)
            cv2.moveWindow(config.WINDOW_NAME, 100, 100)  # window position x=100, y=100
            cv2.imshow(config.WINDOW_NAME, frame_display)

            # 4. Save to file if --save is active
            if writer:
                writer.write(frame_display)

            # -- Keyboard controls --
            key = cv2.waitKey(1) & 0xFF

            if key in [ord('q'), ord('Q'), 27]:      # Q or ESC -> quit
                break

            elif key in [ord('p'), ord('P')]:        # P -> pause
                paused = True
                print("[Main] Paused. Press P again to resume.")

            elif key == ord('+'):                    # + -> increase threshold
                config.CONFIDENCE_THRESHOLD = min(0.95, config.CONFIDENCE_THRESHOLD + 0.05)
                detector.confidence_threshold = config.CONFIDENCE_THRESHOLD
                print(f"[Main] Confidence threshold: {config.CONFIDENCE_THRESHOLD:.2f}")

            elif key == ord('-'):                    # - -> decrease threshold
                config.CONFIDENCE_THRESHOLD = max(0.1, config.CONFIDENCE_THRESHOLD - 0.05)
                detector.confidence_threshold = config.CONFIDENCE_THRESHOLD
                print(f"[Main] Confidence threshold: {config.CONFIDENCE_THRESHOLD:.2f}")

            elif key in [ord('s'), ord('S')]:        # S -> screenshot
                screenshot_count += 1
                fname = f"screenshot_{screenshot_count:03d}.jpg"
                cv2.imwrite(fname, frame_display)
                print(f"[Main] Screenshot saved: {fname}")

    except KeyboardInterrupt:
        print("\n[Main] Stopped by user (Ctrl+C)")

    finally:
        # Cleanup - always runs even if there's an error
        print(f"\n[Main] Total frames processed: {frame_count}")
        cap.release()
        if writer:
            writer.release()
            print(f"[Main] Output saved to: {config.OUTPUT_PATH}")
        cv2.destroyAllWindows()
        print("[Main] Finished.")


if __name__ == "__main__":
    main()