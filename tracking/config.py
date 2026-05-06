# config.py - tracking module
# ============================================================
# Extend dari detection/config.py dengan tambahan
# setting untuk tracking dan counting.
# ============================================================

import sys
import os

# Supaya bisa import dari folder detection/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ── Import semua config detection (re-use) ──
from detection.config import (
    MODEL_NAME,
    CONFIDENCE_THRESHOLD,
    CLASS_PERSON,
    VIDEO_SOURCE,
    DISPLAY_FPS,
    DISPLAY_COUNT,
    DISPLAY_CONFIDENCE,
    BOX_COLOR,
    TEXT_COLOR,
    INFO_BG_COLOR,
    BOX_THICKNESS,
    FONT_SCALE,
    SAVE_OUTPUT,
)

# ── Override ──
WINDOW_NAME = "Retail Analytics - Week 2: Tracking + Counting"
OUTPUT_PATH = "output_week2.mp4"

# ── ByteTrack settings ──
# track_thresh: confidence minimum untuk langsung di-assign ke track aktif
# Deteksi di bawah ini masuk "second association" (ByteTrack trick)
TRACK_THRESH = 0.4

# match_thresh: minimum IoU untuk dianggap "orang yang sama"
MATCH_THRESH = 0.8

# track_buffer: berapa frame sebuah track "bertahan" tanpa deteksi
# Sebelum dianggap hilang dan ID-nya dibuang
# 30 frame = ~1 detik di 30fps. Naikan kalau orang sering hilang sesaat.
TRACK_BUFFER = 30

# frame_rate: FPS video input (dipakai Kalman untuk prediksi motion)
FRAME_RATE = 30

# ── Virtual Line Counting ──
# Garis virtual untuk menghitung orang masuk/keluar.
# Format: (x1, y1, x2, y2) dalam pixel
#
# Cara menentukan posisi:
# - Untuk pintu masuk horizontal: garis vertikal di tengah frame
#   LINE_START = (frame_width // 2, 0)
#   LINE_END   = (frame_width // 2, frame_height)
#
# - Untuk pintu masuk vertikal: garis horizontal di tengah frame
#   LINE_START = (0, frame_height // 2)
#   LINE_END   = (frame_width, frame_height // 2)
#
# Default di bawah: garis vertikal di tengah frame 640px
# Akan di-override otomatis di main.py berdasarkan resolusi video aktual
LINE_START = (320, 0)
LINE_END   = (320, 480)

# Arah mana yang dihitung "masuk" vs "keluar"
# "horizontal": orang bergerak kiri-kanan melewati garis vertikal
#   - bergerak ke KANAN = masuk (IN)
#   - bergerak ke KIRI  = keluar (OUT)
# "vertical": orang bergerak atas-bawah melewati garis horizontal
#   - bergerak ke BAWAH = masuk (IN)
#   - bergerak ke ATAS  = keluar (OUT)
LINE_ORIENTATION = "horizontal"

# Lebar "dead zone" di sekitar garis (pixel)
# Orang harus benar-benar melewati garis (bukan cuma menyentuhnya)
# sebelum crossing dihitung. Cegah false count.
LINE_CROSSING_TOLERANCE = 5

# ── Warna tambahan untuk tracking ──
TRACK_ID_COLOR    = (255, 220, 50)   # Kuning untuk Track ID label
LINE_COLOR        = (0, 200, 255)    # Cyan untuk virtual line
LINE_COLOR_ALERT  = (0, 60, 255)     # Merah kalau ada crossing event
TRAJECTORY_COLOR  = (180, 180, 180)  # Abu untuk jejak pergerakan
TRAJECTORY_LENGTH = 30               # Berapa frame terakhir jejak ditampilkan