# config.py - analytics module
# ============================================================
# Extend dari tracking/config.py dengan setting untuk
# heatmap, queue monitoring, dan demographic estimation.
# ============================================================

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Re-use semua config dari tracking (yang sudah include detection)
from tracking.config import (
    MODEL_NAME, CONFIDENCE_THRESHOLD, CLASS_PERSON,
    VIDEO_SOURCE, DISPLAY_FPS, DISPLAY_COUNT, DISPLAY_CONFIDENCE,
    BOX_COLOR, TEXT_COLOR, INFO_BG_COLOR, BOX_THICKNESS, FONT_SCALE,
    SAVE_OUTPUT, TRACK_THRESH, MATCH_THRESH, TRACK_BUFFER, FRAME_RATE,
    LINE_START, LINE_END, LINE_ORIENTATION, LINE_CROSSING_TOLERANCE,
    TRACK_ID_COLOR, LINE_COLOR, LINE_COLOR_ALERT,
    TRAJECTORY_COLOR, TRAJECTORY_LENGTH,
)

# ── Override ──
WINDOW_NAME = "Retail Analytics - Week 3: Analytics"
OUTPUT_PATH = "output_week3.mp4"

# ============================================================
# HEATMAP
# ============================================================

# Seberapa kuat "panas" yang ditambahkan per orang per frame
# Nilai lebih besar = heatmap lebih cepat jenuh (cocok untuk video pendek)
# Nilai lebih kecil = akumulasi gradual (cocok untuk video panjang / livestream)
HEATMAP_INTENSITY = 3

# Radius Gaussian kernel dalam pixel
# Besar radius = area "panas" lebih lebar per orang
# Kecil radius = akumulasi lebih presisi tapi granular
HEATMAP_RADIUS = 25

# Seberapa transparan overlay heatmap di atas frame asli
# 0.0 = tidak terlihat, 1.0 = heatmap penuh menutupi frame
HEATMAP_ALPHA = 0.45

# Colormap OpenCV untuk heatmap
# cv2.COLORMAP_JET    : biru -> hijau -> kuning -> merah (klasik)
# cv2.COLORMAP_INFERNO: hitam -> ungu -> oranye -> putih (lebih modern)
# cv2.COLORMAP_HOT    : hitam -> merah -> kuning -> putih
import cv2
HEATMAP_COLORMAP = cv2.COLORMAP_JET

# Seberapa sering heatmap di-normalize (dalam frame)
# Normalize terlalu sering = expensive, terlalu jarang = saturasi awal
HEATMAP_NORMALIZE_INTERVAL = 15

# ============================================================
# QUEUE MONITORING
# ============================================================

# Zona kasir / area antrian.
# Format: (x1, y1, x2, y2) sebagai RASIO frame (0.0 - 1.0)
# Pakai rasio supaya tidak perlu ubah kalau resolusi video beda.
#
# Default: Area kasir di sebelah kiri (menyesuaikan video retail CCTV)
# Ganti angka di bawah ini sesuai posisi antrean jika menggunakan video lain.
# (x1=kiri, y1=atas, x2=kanan, y2=bawah)
QUEUE_ZONE = (0.13, 0.15, 0.37, 0.50)
# QUEUE_ZONE = (0.65, 0.60, 1.0, 1.0)

# Threshold jumlah orang di zona kasir yang trigger alert
QUEUE_ALERT_THRESHOLD = 3

# Warna zona kasir
QUEUE_ZONE_COLOR       = (0, 255, 180)   # Cyan-hijau normal
QUEUE_ZONE_COLOR_ALERT = (0, 60, 255)    # Merah saat alert
QUEUE_ZONE_ALPHA       = 0.25            # Transparansi fill zona

# ============================================================
# DEMOGRAPHIC ESTIMATION
# ============================================================

# Seberapa sering DeepFace dijalankan (dalam frame)
# DeepFace cukup lambat (~100-300ms per wajah)
# Jangan run setiap frame - run setiap N frame
DEMO_ANALYSIS_INTERVAL = 15

# Minimum confidence detection wajah sebelum dikirim ke DeepFace
DEMO_MIN_FACE_CONFIDENCE = 0.5

# Ukuran minimum bounding box orang (pixel) sebelum coba analisa wajah
# Wajah terlalu kecil di frame akan menghasilkan estimasi tidak akurat
DEMO_MIN_PERSON_HEIGHT = 80

# Backend DeepFace untuk face detection (sebelum analisa age/gender)
# "opencv"      : paling cepat, akurasi sedang
# "retinaface"  : lebih akurat tapi lebih lambat
# "mtcnn"       : balanced
DEMO_DETECTOR_BACKEND = "opencv"

# Berapa hasil analisa terakhir yang disimpan untuk statistik agregat
# (rolling window untuk chart demografi)
DEMO_HISTORY_SIZE = 50

# Warna label demografi di atas bounding box
DEMO_LABEL_COLOR = (255, 180, 50)

# ============================================================
# DISPLAY
# ============================================================

# Panel info sebelah kanan bawah untuk demografi
DEMO_PANEL_WIDTH  = 220
DEMO_PANEL_HEIGHT = 160