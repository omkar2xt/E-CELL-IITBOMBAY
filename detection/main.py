# main.py
# ============================================================
# Entry point. Jalankan: python main.py
#
# Untuk pakai video file:
#   python main.py --source path/ke/video.mp4
#
# Untuk pakai webcam:
#   python main.py --source 0
#
# Untuk simpan output:
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
        description="Week 1: Person Detection Pipeline"
    )
    parser.add_argument(
        "--source",
        default=str(config.VIDEO_SOURCE),
        help="Path ke video file, atau angka untuk webcam (0, 1, ...)"
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
        help="Simpan output video ke file"
    )
    return parser.parse_args()


def open_video_source(source_str: str) -> cv2.VideoCapture:
    """
    Buka video dari file atau webcam.
    Source bisa berupa:
    - "0" atau "1" → webcam index
    - "path/ke/file.mp4" → video file
    """
    # Coba parse sebagai integer (webcam index)
    try:
        source = int(source_str)
        print(f"[Main] Membuka webcam index: {source}")
    except ValueError:
        source = source_str
        print(f"[Main] Membuka video file: {source}")

    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"[ERROR] Tidak bisa membuka source: {source}")
        print("Pastikan:")
        print("  - Path video benar")
        print("  - Webcam tersedia (coba index 0 atau 1)")
        sys.exit(1)

    return cap


def setup_video_writer(cap: cv2.VideoCapture, output_path: str):
    """Setup VideoWriter kalau --save diaktifkan."""
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    print(f"[Main] Output akan disimpan ke: {output_path}")
    return writer


def print_controls():
    print("\n" + "="*50)
    print("  Retail Analytics — Week 1: Detection")
    print("="*50)
    print("  Kontrol keyboard:")
    print("  [Q] atau [ESC] → Keluar")
    print("  [P]            → Pause / Resume")
    print("  [+] / [-]      → Naikkan/turunkan confidence threshold")
    print("  [S]            → Screenshot frame ini")
    print("="*50 + "\n")


def main():
    args = parse_args()

    # Override config dari argumen command line
    config.CONFIDENCE_THRESHOLD = args.conf
    config.SAVE_OUTPUT = args.save

    print_controls()

    # ── Inisialisasi komponen ──
    detector = PersonDetector()
    visualizer = Visualizer()
    cap = open_video_source(args.source)
    writer = setup_video_writer(cap, config.OUTPUT_PATH) if args.save else None

    # Info video
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_source = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[Main] Resolusi: {width}x{height}, FPS source: {fps_source:.1f}")
    if total_frames > 0:
        duration = total_frames / fps_source if fps_source > 0 else 0
        print(f"[Main] Total frames: {total_frames} ({duration:.1f} detik)\n")

    # ── Main loop ──
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

            # Baca frame berikutnya
            ret, frame = cap.read()

            if not ret:
                # Video file habis → loop dari awal (kalau file), atau stop (webcam)
                if isinstance(cap.get(cv2.CAP_PROP_POS_FRAMES), float):
                    print("[Main] Video selesai. Loop dari awal...")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    print("[Main] Stream berakhir.")
                    break

            frame_count += 1

            # ── Core pipeline ──

            # 1. Detect semua orang di frame ini
            detections = detector.detect(frame)

            # 2. Gambar hasil ke frame
            frame_display = visualizer.draw(frame, detections)

            # 3. Tampilkan
            cv2.namedWindow(config.WINDOW_NAME, cv2.WINDOW_NORMAL)
            cv2.moveWindow(config.WINDOW_NAME, 100, 100)  # posisi x=100, y=100 dari pojok kiri atas layar
            cv2.imshow(config.WINDOW_NAME, frame_display)

            # 4. Simpan ke file kalau --save aktif
            if writer:
                writer.write(frame_display)

            # ── Keyboard controls ──
            key = cv2.waitKey(1) & 0xFF

            if key in [ord('q'), ord('Q'), 27]:      # Q atau ESC → keluar
                break

            elif key in [ord('p'), ord('P')]:         # P → pause
                paused = True
                print("[Main] Paused. Tekan P lagi untuk resume.")

            elif key == ord('+'):                     # + → naikkan threshold
                config.CONFIDENCE_THRESHOLD = min(0.95, config.CONFIDENCE_THRESHOLD + 0.05)
                detector.confidence_threshold = config.CONFIDENCE_THRESHOLD
                print(f"[Main] Confidence threshold: {config.CONFIDENCE_THRESHOLD:.2f}")

            elif key == ord('-'):                     # - → turunkan threshold
                config.CONFIDENCE_THRESHOLD = max(0.1, config.CONFIDENCE_THRESHOLD - 0.05)
                detector.confidence_threshold = config.CONFIDENCE_THRESHOLD
                print(f"[Main] Confidence threshold: {config.CONFIDENCE_THRESHOLD:.2f}")

            elif key in [ord('s'), ord('S')]:         # S → screenshot
                screenshot_count += 1
                fname = f"screenshot_{screenshot_count:03d}.jpg"
                cv2.imwrite(fname, frame_display)
                print(f"[Main] Screenshot disimpan: {fname}")

    except KeyboardInterrupt:
        print("\n[Main] Dihentikan oleh user (Ctrl+C)")

    finally:
        # Cleanup — selalu dijalankan walau ada error
        print(f"\n[Main] Total frames diproses: {frame_count}")
        cap.release()
        if writer:
            writer.release()
            print(f"[Main] Output disimpan ke: {config.OUTPUT_PATH}")
        cv2.destroyAllWindows()
        print("[Main] Selesai.")


if __name__ == "__main__":
    main()