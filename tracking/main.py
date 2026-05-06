# main.py - tracking module
# ============================================================
# Entry point Week 2: Tracking + Counting
#
# Cara pakai:
#   python main.py --source 0                    webcam
#   python main.py --source video.mp4            video file
#   python main.py --source video.mp4 --save     simpan output
#   python main.py --source video.mp4 --headless tanpa GUI
#
# Konfigurasi garis counting:
#   python main.py --source video.mp4 --line-orientation vertical
# ============================================================

import cv2
import argparse
import sys
import os

# Tambahkan path ke detection/ supaya bisa import config detection
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'detection'))

import config as config
from tracker import PersonTracker
from counter import LineCounter
from visualizer import TrackingVisualizer


def parse_args():
    parser = argparse.ArgumentParser(description="Week 2: Tracking + Counting")
    parser.add_argument("--source", default=str(config.VIDEO_SOURCE),
                        help="Path video atau index webcam (0, 1, ...)")
    parser.add_argument("--conf", type=float, default=config.TRACK_THRESH,
                        help="Confidence threshold")
    parser.add_argument("--save", action="store_true",
                        help="Simpan output ke file")
    parser.add_argument("--headless", action="store_true",
                        help="Jalankan tanpa GUI window")
    parser.add_argument("--line-orientation", choices=["horizontal", "vertical"],
                        default=config.LINE_ORIENTATION,
                        help="Orientasi garis counting (default: horizontal)")
    return parser.parse_args()


def open_source(source_str: str) -> cv2.VideoCapture:
    try:
        source = int(source_str)
        print(f"[Main] Membuka webcam: {source}")
    except ValueError:
        source = source_str
        print(f"[Main] Membuka video: {source}")

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Tidak bisa buka source: {source}")
        sys.exit(1)
    return cap


def get_frame_dimensions(cap: cv2.VideoCapture):
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    return w, h, fps


def build_counting_line(w: int, h: int, orientation: str):
    """
    Buat posisi garis counting berdasarkan resolusi video aktual.

    Garis selalu di tengah frame:
    - orientation "horizontal" -> garis vertikal di x = w/2
    - orientation "vertical"   -> garis horizontal di y = h/2

    Kamu bisa override manual di config.py kalau mau posisi berbeda.
    """
    if orientation == "horizontal":
        # Garis vertikal agak ke kanan (75% dari lebar frame)
        # Kamu bisa mengubah 0.75 menjadi angka lain (contoh: 0.8 untuk lebih kanan lagi, 0.5 untuk di tengah)
        x_pos = int(w * 0.85)
        line_start = (x_pos, 0)
        line_end   = (x_pos, h)
    else:
        # Garis horizontal di tengah
        line_start = (0, h // 2)
        line_end   = (w, h // 2)

    print(f"[Main] Counting line: {line_start} -> {line_end} ({orientation})")
    return line_start, line_end


def setup_writer(cap, path):
    w, h, fps = get_frame_dimensions(cap)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (w, h))
    print(f"[Main] Output: {path}")
    return writer


def print_controls():
    print("\n" + "="*52)
    print("  Retail Analytics - Week 2: Tracking + Counting")
    print("="*52)
    print("  [Q] / [ESC]  Keluar")
    print("  [P]          Pause / Resume")
    print("  [R]          Reset counter IN/OUT")
    print("  [S]          Screenshot")
    print("  [+] / [-]    Confidence threshold")
    print("="*52 + "\n")


def main():
    args = parse_args()
    config.LINE_ORIENTATION = args.line_orientation
    config.TRACK_THRESH = args.conf

    print_controls()

    # ── Init komponen ──
    tracker   = PersonTracker()
    visualizer = TrackingVisualizer()
    cap       = open_source(args.source)

    w, h, fps = get_frame_dimensions(cap)
    line_start, line_end = build_counting_line(w, h, args.line_orientation)
    counter = LineCounter(line_start, line_end)

    writer = setup_writer(cap, config.OUTPUT_PATH) if (args.save or args.headless) else None

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames > 0:
        print(f"[Main] Video: {w}x{h} @ {fps:.0f}fps | {total_frames} frames\n")

    # ── Main loop ──
    frame_count = 0
    paused = False
    screenshot_count = 0
    cleanup_interval = 300   # bersihkan dead tracks setiap 300 frame

    try:
        while True:
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
                    print("[Main] Video selesai, loop ulang...")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                break

            frame_count += 1

            # ── Core pipeline ──

            # 1. Track semua orang di frame ini
            tracked_persons = tracker.update(frame)

            # 2. Update counter (cek crossing)
            counter.update(tracked_persons)

            # 3. Gambar semua overlay
            frame_out = visualizer.draw(
                frame,
                tracked_persons,
                counter,
                tracker.trajectories
            )

            # 4. Tampilkan / simpan
            if not args.headless:
                cv2.namedWindow(config.WINDOW_NAME, cv2.WINDOW_NORMAL)
                cv2.moveWindow(config.WINDOW_NAME, 100, 100)
                cv2.imshow(config.WINDOW_NAME, frame_out)
            else:
                if frame_count % 30 == 0:
                    print(
                        f"[Main] Frame {frame_count:4d} | "
                        f"In frame: {len(tracked_persons):2d} | "
                        f"IN: {counter.count_in} OUT: {counter.count_out} | "
                        f"Occupancy: {counter.current_occupancy}"
                    )

            if writer:
                writer.write(frame_out)

            # Bersihkan trajectory lama
            if frame_count % cleanup_interval == 0:
                active = {p.track_id for p in tracked_persons}
                tracker.cleanup_old_tracks(active)

            # ── Keyboard ──
            if args.headless:
                continue

            key = cv2.waitKey(1) & 0xFF

            if key in [ord('q'), ord('Q'), 27]:
                break
            elif key in [ord('p'), ord('P')]:
                paused = True
                print("[Main] Paused...")
            elif key in [ord('r'), ord('R')]:
                counter.reset_counts()
                print("[Main] Counter direset.")
            elif key == ord('+'):
                config.TRACK_THRESH = min(0.95, config.TRACK_THRESH + 0.05)
                print(f"[Main] Confidence: {config.TRACK_THRESH:.2f}")
            elif key == ord('-'):
                config.TRACK_THRESH = max(0.1, config.TRACK_THRESH - 0.05)
                print(f"[Main] Confidence: {config.TRACK_THRESH:.2f}")
            elif key in [ord('s'), ord('S')]:
                screenshot_count += 1
                fname = f"screenshot_w2_{screenshot_count:03d}.jpg"
                cv2.imwrite(fname, frame_out)
                print(f"[Main] Screenshot: {fname}")

    except KeyboardInterrupt:
        print("\n[Main] Dihentikan.")

    finally:
        print(f"\n[Main] Summary:")
        print(f"  Frames diproses : {frame_count}")
        print(f"  Total IN        : {counter.count_in}")
        print(f"  Total OUT       : {counter.count_out}")
        print(f"  Occupancy akhir : {counter.current_occupancy}")
        cap.release()
        if writer:
            writer.release()
            print(f"  Output disimpan : {config.OUTPUT_PATH}")
        cv2.destroyAllWindows()
        print("[Main] Selesai.")


if __name__ == "__main__":
    main()