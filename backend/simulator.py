# StorePulse AI — What-If Layout Simulator & Heuristic Engine
# Developer: Omkar Gurav
#
# IMPORTANT DISCLAIMER:
# This is a transparent heuristic estimation model, not a validated
# customer-flow simulation engine. Moving virtual shelves does NOT
# accurately predict real customer behavior. All outputs are labeled
# as heuristic estimates with documented assumptions and uncertainty.
#
# The model uses simple geometric reasoning about:
#   - Distance from entrance to destinations
#   - Available walking space vs. obstacles
#   - Zone locations and assumed demand weights
#   - Path conflicts from shelf placements

import math
import time
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field


# ── Data models ──────────────────────────────────────────────────────


@dataclass
class ShelfElement:
    """A draggable shelf/obstacle on the floor plan."""
    id: str
    element_type: str       # shelf|checkout|display|obstacle|entrance|exit
    x: float                # position ratio 0–1
    y: float                # position ratio 0–1
    width: float            # size ratio 0–1
    height: float           # size ratio 0–1
    rotation: float = 0.0   # degrees
    label: str = ""


@dataclass
class LayoutConfig:
    """A complete store layout: shelves + zones."""
    id: str
    name: str
    description: str
    elements: List[ShelfElement] = field(default_factory=list)
    zones: List[Dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    is_baseline: bool = False


# ── Simulation ────────────────────────────────────────────────────────


class LayoutSimulator:
    """
    Heuristic layout simulation model.

    Given a proposed layout, estimates changes to:
      - Customer walking distance
      - Route conflicts
      - Zone accessibility score
      - Space utilization
      - Flow friction estimate

    All outputs are explicitly labeled as heuristic estimates.
    """

    # Demand weights by zone type — higher = more frequently visited
    # These are configurable assumptions, not empirically validated
    ZONE_DEMAND_WEIGHTS = {
        "entrance":    0.5,
        "checkout":    1.0,
        "electronics": 0.8,
        "grocery":     0.9,
        "promo":       0.6,
        "display":     0.5,
        "restricted":  0.0,
    }

    def simulate(
        self,
        baseline: LayoutConfig,
        proposed: LayoutConfig,
        baseline_analytics: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Run simulation comparing baseline vs. proposed layout.

        baseline_analytics: real measured data from zone_analytics_engine (if available).
        Returns a comparison report.
        """

        baseline_metrics = self._compute_layout_metrics(baseline)
        proposed_metrics = self._compute_layout_metrics(proposed)

        comparison = self._build_comparison(
            baseline_metrics,
            proposed_metrics,
            baseline_analytics
        )

        return {
            "model": "StorePulse AI Heuristic Layout Simulator v1",
            "disclaimer": (
                "All proposed values are heuristic estimates based on geometric "
                "layout analysis. They do NOT predict real customer behavior. "
                "Field validation is required before operational decisions."
            ),
            "assumptions": [
                "Customer traffic is assumed proportional to zone demand weights",
                "Walking distance is approximated as Manhattan distance between zones",
                "Obstacle density reduces available path space linearly",
                "No real customer preference data is incorporated",
                "Queue build-up is not dynamically simulated",
            ],
            "baseline": {
                "layout_id": baseline.id,
                "layout_name": baseline.name,
                "metrics": baseline_metrics,
            },
            "proposed": {
                "layout_id": proposed.id,
                "layout_name": proposed.name,
                "metrics": proposed_metrics,
            },
            "comparison": comparison,
            "generated_at": time.time(),
        }

    def _compute_layout_metrics(self, layout: LayoutConfig) -> Dict[str, Any]:
        """Compute geometric metrics for a single layout."""
        elements = layout.elements
        zones = layout.zones

        # Space utilization: fraction occupied by shelves/obstacles
        total_element_area = sum(
            self._norm_element(e)[2] * self._norm_element(e)[3]
            for e in elements
            if e.element_type not in ("entrance", "exit")
        )
        space_utilization = round(min(1.0, total_element_area) * 100, 1)
        free_space = round(100.0 - space_utilization, 1)

        # Walking distance estimate: entrance to each zone centroid
        entrance = self._find_entrance(elements)
        zone_distances = {}
        for zone in zones:
            zx, zy = self._zone_centroid(zone.get("polygon", []))
            dist = self._manhattan_distance(entrance, (zx, zy))
            demand = self.ZONE_DEMAND_WEIGHTS.get(zone.get("type", "display"), 0.5)
            zone_distances[zone.get("id", "?")] = {
                "distance_units": round(dist, 3),
                "demand_weight": demand,
                "weighted_distance": round(dist * demand, 3)
            }

        avg_weighted_dist = (
            sum(v["weighted_distance"] for v in zone_distances.values()) / max(len(zone_distances), 1)
        )

        # Route conflict score: overlapping elements reduce walkability
        conflict_score = self._estimate_conflicts(elements)

        # Checkout accessibility
        checkout_dist = self._checkout_distance(elements, zones, entrance)

        # Estimated layout flow friction (0-100 heuristic decision index)
        occ_penalty = max(0.0, (space_utilization - 25.0) * 1.5)
        dist_penalty = min(50.0, checkout_dist * 50.0)
        est_friction = round(min(100.0, max(0.0, conflict_score * 0.4 + occ_penalty * 0.35 + dist_penalty * 0.25)), 1)

        return {
            "space_utilization_pct": space_utilization,
            "free_space_pct": free_space,
            "element_count": len(elements),
            "zone_count": len(zones),
            "avg_weighted_walking_distance": round(avg_weighted_dist, 3),
            "checkout_distance": round(checkout_dist, 3),
            "route_conflict_score": round(conflict_score, 1),
            "estimated_layout_friction": est_friction,
            "zone_distances": zone_distances,
        }

    def _build_comparison(
        self,
        baseline: Dict,
        proposed: Dict,
        real_analytics: Optional[Dict]
    ) -> List[Dict]:
        """Build a row-by-row comparison table."""
        rows = []

        def row(metric, b_val, p_val, unit="", lower_is_better=True):
            if isinstance(b_val, float) and isinstance(p_val, float) and b_val != 0:
                abs_diff = round(p_val - b_val, 3)
                pct_diff = round((abs_diff / b_val) * 100, 1)
            else:
                abs_diff = p_val - b_val if isinstance(b_val, (int, float)) else "N/A"
                pct_diff = "N/A"

            if isinstance(abs_diff, float):
                better = (abs_diff < 0) if lower_is_better else (abs_diff > 0)
                direction = "BETTER" if better else ("SAME" if abs_diff == 0 else "WORSE")
            else:
                direction = "N/A"

            rows.append({
                "metric": metric,
                "baseline": f"{b_val}{unit}",
                "proposed": f"{p_val}{unit}",
                "absolute_diff": f"{abs_diff}{unit}" if abs_diff != "N/A" else "N/A",
                "pct_diff": f"{pct_diff}%" if pct_diff != "N/A" else "N/A",
                "direction": direction,
                "source": "heuristic_estimate",
                "confidence": "LOW",
            })

        row("Space Utilization", baseline["space_utilization_pct"], proposed["space_utilization_pct"], "%", lower_is_better=False)
        row("Free Walking Space", baseline["free_space_pct"], proposed["free_space_pct"], "%", lower_is_better=False)
        row("Avg Weighted Walking Distance", baseline["avg_weighted_walking_distance"], proposed["avg_weighted_walking_distance"], " units", lower_is_better=True)
        row("Checkout Accessibility Distance", baseline["checkout_distance"], proposed["checkout_distance"], " units", lower_is_better=True)
        row("Route Conflict Score", baseline["route_conflict_score"], proposed["route_conflict_score"], "", lower_is_better=True)
        row("Estimated Layout Flow Friction", baseline.get("estimated_layout_friction", 0.0), proposed.get("estimated_layout_friction", 0.0), "", lower_is_better=True)
        row("Element Count", baseline["element_count"], proposed["element_count"], " items", lower_is_better=False)

        # Inject real analytics if available
        if real_analytics:
            for zone_id, zstats in real_analytics.items():
                rows.append({
                    "metric": f"[MEASURED] {zstats.get('zone_name', zone_id)} Avg Dwell",
                    "baseline": f"{zstats.get('avg_dwell_seconds', 0):.1f}s",
                    "proposed": "Insufficient data",
                    "absolute_diff": "N/A",
                    "pct_diff": "N/A",
                    "direction": "N/A",
                    "source": "real_measurement",
                    "confidence": zstats.get("sample_count", 0) >= 10 and "HIGH" or "MEDIUM",
                })

        return rows

    # ── Geometry helpers ───────────────────────────────────────────────

    @staticmethod
    def _norm_element(e: ShelfElement) -> Tuple[float, float, float, float]:
        """Normalize element coordinates to [0, 1] relative to 800x500 canvas if in pixels."""
        x = e.x / 800.0 if e.x > 1.0 else e.x
        y = e.y / 500.0 if e.y > 1.0 else e.y
        w = e.width / 800.0 if e.width > 1.0 else e.width
        h = e.height / 500.0 if e.height > 1.0 else e.height
        return x, y, w, h

    def _find_entrance(self, elements: List[ShelfElement]) -> Tuple[float, float]:
        for e in elements:
            if e.element_type == "entrance":
                x, y, w, h = self._norm_element(e)
                return (x + w / 2, y + h / 2)
        return (0.1, 0.9)  # Default bottom-left assumption

    def _zone_centroid(self, polygon: List) -> Tuple[float, float]:
        if not polygon:
            return (0.5, 0.5)
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    def _manhattan_distance(self, a: Tuple, b: Tuple) -> float:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _estimate_conflicts(self, elements: List[ShelfElement]) -> float:
        """
        Estimate route conflicts by counting overlapping elements.
        Score 0 (no overlap) → 100 (maximum overlap).
        """
        if len(elements) < 2:
            return 0.0
        overlap_count = 0
        for i, e1 in enumerate(elements):
            for e2 in elements[i+1:]:
                if self._rects_overlap(e1, e2):
                    overlap_count += 1
        # Normalize against max possible overlaps
        max_overlaps = len(elements) * (len(elements) - 1) / 2
        return round((overlap_count / max(max_overlaps, 1)) * 100, 1)

    def _rects_overlap(self, a: ShelfElement, b: ShelfElement) -> bool:
        ax, ay, aw, ah = self._norm_element(a)
        bx, by, bw, bh = self._norm_element(b)
        return not (
            ax + aw <= bx or
            bx + bw <= ax or
            ay + ah <= by or
            by + bh <= ay
        )

    def _checkout_distance(
        self,
        elements: List[ShelfElement],
        zones: List[Dict],
        entrance: Tuple[float, float]
    ) -> float:
        for zone in zones:
            if zone.get("type") == "checkout":
                centroid = self._zone_centroid(zone.get("polygon", []))
                return self._manhattan_distance(entrance, centroid)
        # No checkout zone defined
        for e in elements:
            if e.element_type == "checkout":
                x, y, w, h = self._norm_element(e)
                return self._manhattan_distance(entrance, (x + w / 2, y + h / 2))
        return 0.5  # Unknown


# ── Data store for layouts ─────────────────────────────────────────────


class LayoutStore:
    """
    Simple in-memory store for layout configurations.
    Persists as long as the server is running.
    """

    def __init__(self):
        self._layouts: Dict[str, LayoutConfig] = {}
        self._baseline_id: Optional[str] = None
        self._init_defaults()

    def _init_defaults(self):
        """Initialize with a sample baseline layout."""
        baseline = LayoutConfig(
            id="baseline",
            name="Current Layout (Baseline)",
            description="Default store layout loaded at startup",
            is_baseline=True,
            elements=[
                ShelfElement("s1", "shelf",    0.25, 0.1,  0.1, 0.35, label="Shelf A"),
                ShelfElement("s2", "shelf",    0.40, 0.1,  0.1, 0.35, label="Shelf B"),
                ShelfElement("s3", "shelf",    0.55, 0.1,  0.1, 0.35, label="Shelf C"),
                ShelfElement("s4", "shelf",    0.70, 0.1,  0.1, 0.35, label="Shelf D"),
                ShelfElement("s5", "shelf",    0.25, 0.55, 0.1, 0.35, label="Shelf E"),
                ShelfElement("s6", "shelf",    0.40, 0.55, 0.1, 0.35, label="Shelf F"),
                ShelfElement("s7", "shelf",    0.55, 0.55, 0.1, 0.35, label="Shelf G"),
                ShelfElement("c1", "checkout", 0.05, 0.1,  0.15, 0.35, label="Checkout"),
                ShelfElement("e1", "entrance", 0.0,  0.75, 0.1,  0.2, label="Entrance"),
                ShelfElement("d1", "display",  0.38, 0.15, 0.08, 0.25, label="Promo"),
            ],
            zones=[],
        )
        self._layouts["baseline"] = baseline
        self._baseline_id = "baseline"

    def save_layout(self, layout: LayoutConfig) -> LayoutConfig:
        self._layouts[layout.id] = layout
        if layout.is_baseline:
            self._baseline_id = layout.id
        return layout

    def get_layout(self, layout_id: str) -> Optional[LayoutConfig]:
        return self._layouts.get(layout_id)

    def list_layouts(self) -> List[Dict]:
        return [
            {
                "id": l.id,
                "name": l.name,
                "description": l.description,
                "is_baseline": l.is_baseline,
                "created_at": l.created_at,
                "element_count": len(l.elements),
            }
            for l in self._layouts.values()
        ]

    def delete_layout(self, layout_id: str) -> bool:
        if layout_id == self._baseline_id:
            return False  # Cannot delete baseline
        return self._layouts.pop(layout_id, None) is not None

    def get_baseline(self) -> Optional[LayoutConfig]:
        return self._layouts.get(self._baseline_id)


# Singletons
layout_simulator = LayoutSimulator()
layout_store = LayoutStore()
