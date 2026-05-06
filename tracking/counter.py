# counter.py
# ============================================================
# Virtual line crossing counter.
#
# Cara kerja:
# 1. Definisikan garis virtual di frame (misal di pintu masuk)
# 2. Setiap frame, cek posisi setiap tracked person terhadap garis
# 3. Kalau seseorang berpindah dari satu sisi ke sisi lain → crossing
# 4. Arah crossing menentukan IN atau OUT
#
# Kenapa pakai bottom_center bukan center?
# Kaki orang adalah referensi posisi yang lebih stabil.
# Kalau pakai center, orang yang membungkuk bisa trigger false crossing.
# ============================================================

from typing import Dict, Tuple, List
from tracker import TrackedPerson
import config as config


class LineCounter:
    """
    Menghitung orang yang melewati garis virtual.

    State per track_id:
    - "side": sisi mana orang ini terakhir terlihat (A atau B)
    - Saat side berubah → crossing terjadi
    """

    def __init__(self, line_start: Tuple[int, int], line_end: Tuple[int, int]):
        self.line_start = line_start
        self.line_end = line_end
        self.orientation = config.LINE_ORIENTATION
        self.tolerance = config.LINE_CROSSING_TOLERANCE

        # Counter
        self.count_in = 0
        self.count_out = 0

        # State terakhir tiap track: {"side": "A" atau "B"}
        # "A" = kiri/atas dari garis
        # "B" = kanan/bawah dari garis
        self._track_states: Dict[int, str] = {}

        # List crossing event di frame ini (untuk visual flash)
        # Format: (track_id, direction)  direction = "IN" atau "OUT"
        self.current_crossings: List[Tuple[int, str]] = []

    def update(self, tracked_persons: List[TrackedPerson]):
        """
        Proses semua orang di frame ini.
        Update counter kalau ada yang crossing.
        """
        self.current_crossings = []  # reset event per frame

        for person in tracked_persons:
            self._check_crossing(person)

    def _get_side(self, point: Tuple[int, int]) -> str:
        """
        Tentukan sisi mana point berada relatif terhadap garis.
        Returns "A" atau "B".

        Untuk garis horizontal (LINE_ORIENTATION = "vertical"):
            A = di atas garis (y < line_y)
            B = di bawah garis (y > line_y)

        Untuk garis vertikal (LINE_ORIENTATION = "horizontal"):
            A = di kiri garis (x < line_x)
            B = di kanan garis (x > line_x)
        """
        px, py = point

        if self.orientation == "horizontal":
            # Garis vertikal, orang bergerak kiri-kanan
            line_x = self.line_start[0]
            if px < line_x - self.tolerance:
                return "A"
            elif px > line_x + self.tolerance:
                return "B"
            else:
                return "ZONE"  # Di dalam dead zone, tidak dihitung
        else:
            # Garis horizontal, orang bergerak atas-bawah
            line_y = self.line_start[1]
            if py < line_y - self.tolerance:
                return "A"
            elif py > line_y + self.tolerance:
                return "B"
            else:
                return "ZONE"

    def _check_crossing(self, person: TrackedPerson):
        """
        Cek apakah orang ini baru saja melewati garis.
        """
        tid = person.track_id
        point = person.bottom_center
        current_side = self._get_side(point)

        # Skip kalau di dead zone
        if current_side == "ZONE":
            return

        # Kalau track baru (belum ada di state), simpan posisi awal
        if tid not in self._track_states:
            self._track_states[tid] = current_side
            return

        prev_side = self._track_states[tid]

        # Crossing terjadi kalau sisi berubah
        if prev_side != current_side:
            if self.orientation == "horizontal":
                # Garis vertikal: A=kiri, B=kanan
                # B -> A = bergerak ke kiri  = IN (dari kanan ke kiri)
                # A -> B = bergerak ke kanan = OUT (dari kiri ke kanan)
                if prev_side == "B" and current_side == "A":
                    self.count_in += 1
                    self.current_crossings.append((tid, "IN"))
                elif prev_side == "A" and current_side == "B":
                    self.count_out += 1
                    self.current_crossings.append((tid, "OUT"))
            else:
                # Garis horizontal: A=atas, B=bawah
                # A -> B = bergerak ke bawah = IN
                # B -> A = bergerak ke atas  = OUT
                if prev_side == "A" and current_side == "B":
                    self.count_in += 1
                    self.current_crossings.append((tid, "IN"))
                elif prev_side == "B" and current_side == "A":
                    self.count_out += 1
                    self.current_crossings.append((tid, "OUT"))

            # Update state
            self._track_states[tid] = current_side

    @property
    def current_occupancy(self) -> int:
        """
        Estimasi jumlah orang yang sedang berada di dalam area.
        IN - OUT. Bisa negatif kalau video tidak mulai dari awal
        atau ada yang keluar tanpa tercatat masuk.
        """
        return max(0, self.count_in - self.count_out)

    def has_crossing_this_frame(self) -> bool:
        return len(self.current_crossings) > 0

    def reset_counts(self):
        """Reset counter (misal untuk laporan per jam)."""
        self.count_in = 0
        self.count_out = 0
        self._track_states.clear()
        self.current_crossings.clear()