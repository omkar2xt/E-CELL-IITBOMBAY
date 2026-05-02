# config.py
# ============================================================
# Semua konfigurasi project ada di sini.
# Kalau mau ubah setting, cukup edit file ini saja.
# ============================================================

# --- Model ---
MODEL_NAME = "yolo11n.pt"       # n=nano (paling ringan & cepat)
                                 # Pilihan lain: yolo11s.pt, yolo11m.pt, yolo11l.pt
                                 # Makin besar = makin akurat tapi makin lambat
                                 # Untuk development, pakai nano dulu

# --- Detection ---
CONFIDENCE_THRESHOLD = 0.4      # Min confidence buat dianggap "person"
                                 # 0.4 = 40%. Terlalu rendah → banyak false positive
                                 #             Terlalu tinggi → orang kelewat (false negative)
                                 # Untuk retail indoor, 0.35-0.5 biasanya bagus

CLASS_PERSON = 0                 # Di COCO dataset, class index 0 = "person"
                                 # YOLO filter otomatis, jadi hanya orang yang di-detect

# --- Video Input ---
# Ganti ke path video kamu, atau 0 untuk webcam
# Contoh: VIDEO_SOURCE = "data/mall_sample.mp4"
# Contoh: VIDEO_SOURCE = 0   ← webcam default
VIDEO_SOURCE = 0                 # Default: webcam

# --- Display ---
WINDOW_NAME = "Retail Analytics - Week 1: Detection"
DISPLAY_FPS = True              # Tampilkan FPS di pojok kiri atas
DISPLAY_COUNT = True            # Tampilkan jumlah orang yang terdeteksi
DISPLAY_CONFIDENCE = True       # Tampilkan confidence score di tiap box

# Warna bounding box (BGR format, bukan RGB!)
# BGR: (Blue, Green, Red)
BOX_COLOR = (0, 255, 100)       # Hijau terang
TEXT_COLOR = (255, 255, 255)    # Putih
INFO_BG_COLOR = (0, 0, 0)       # Background teks hitam
BOX_THICKNESS = 2
FONT_SCALE = 0.55

# --- Output (opsional) ---
SAVE_OUTPUT = False             # Set True kalau mau simpan video hasil
OUTPUT_PATH = "output_week1.mp4"