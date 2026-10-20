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
    description: str = ""
    elements: List[ShelfElement] = field(default_factory=list)
    zones: List[Dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    is_baseline: bool = False


# ── Simulation ────────────────────────────────────────────────────────


class LayoutSimulator:
    """
    Heuristic layout simulation model.

    Given a proposed layout and baseline layout (plus optional live analytics & transitions),
    estimates changes to:
      - Customer walking distance
      - Route conflicts & overlapping obstacles
      - Zone accessibility and aisle clearance
      - Zone-by-zone predicted congestion risk & bottleneck probabilities
      - Space utilization
      - Layout flow friction index

    All outputs are explicitly labeled as heuristic estimates.
    """

    # Default demand weights by zone type — higher = more frequently visited
    # Used when empirical transition data is insufficient (< 5 transitions)
    ZONE_DEMAND_WEIGHTS = {
        "entrance":    0.5,
        "checkout":    1.0,
        "electronics": 0.8,
        "grocery":     0.9,
        "promo":       0.6,
        "display":     0.5,
        "restricted":  0.0,
    }

    def validate_layout(self, layout: LayoutConfig) -> Dict[str, Any]:
        """
        Validate layout geometry to prevent invalid placement, out-of-bounds items,
        or accidental overlaps before simulation or saving.
        """
        errors: List[str] = []
        warnings: List[str] = []
        overlap_pairs: List[Dict[str, Any]] = []

        elements = layout.elements or []
        has_entrance = any(e.element_type == "entrance" for e in elements)
        has_checkout = any(e.element_type == "checkout" for e in elements)

        if not has_entrance:
            warnings.append("No entrance element defined; defaulting to bottom-left entrance assumption (0.1, 0.9).")
        if not has_checkout:
            warnings.append("No checkout element defined; checkout accessibility cannot be measured accurately.")

        # Check bounds and dimensions
        for e in elements:
            x, y, w, h = self._norm_element(e)
            if w <= 0.0 or h <= 0.0:
                errors.append(f"Element '{e.id}' ({e.label or e.element_type}) has non-positive dimensions.")
            if x < -0.05 or y < -0.05 or (x + w) > 1.05 or (y + h) > 1.05:
                warnings.append(f"Element '{e.id}' ({e.label or e.element_type}) extends beyond the store boundary.")

        # Check overlaps among physical fixtures (shelves, displays, obstacles, checkouts)
        physical_types = {"shelf", "display", "obstacle", "checkout"}
        for i, e1 in enumerate(elements):
            if e1.element_type not in physical_types:
                continue
            for e2 in elements[i + 1:]:
                if e2.element_type not in physical_types:
                    continue
                if self._rects_overlap(e1, e2):
                    overlap_pairs.append({
                        "element_1": e1.id,
                        "label_1": e1.label or e1.element_type,
                        "element_2": e2.id,
                        "label_2": e2.label or e2.element_type,
                    })

        if overlap_pairs:
            warnings.append(f"Detected {len(overlap_pairs)} overlapping fixture pairs causing aisle obstruction.")

        return {
            "is_valid": len(errors) == 0,
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "overlap_pairs": overlap_pairs,
            "overlap_count": len(overlap_pairs),
        }

    def simulate(
        self,
        baseline: LayoutConfig,
        proposed: LayoutConfig,
        baseline_analytics: Optional[Dict] = None,
        transition_data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Run simulation comparing baseline vs. proposed layout.

        baseline_analytics: real measured data from zone_analytics_engine (if available).
        transition_data: zone-to-zone transitions and empirical probabilities.
        Returns a comprehensive comparison report.
        """
        # Determine empirical demand weights if transition data is sufficient
        demand_weights = dict(self.ZONE_DEMAND_WEIGHTS)
        used_empirical_transitions = False
        assumptions = [
            "Customer traffic is approximated from zone geometry and accessibility",
            "Walking distance is approximated as Manhattan distance between centroids",
            "Obstacle placement reduces available aisle width and increases collision risk",
            "Queue build-up is modeled as an accessibility penalty around registers",
        ]

        if transition_data and transition_data.get("data_sufficient") and transition_data.get("transitions"):
            used_empirical_transitions = True
            # Weight zones by total observed transition arrivals/departures
            for t in transition_data["transitions"]:
                to_z = t.get("to_zone")
                if to_z:
                    demand_weights[to_z] = demand_weights.get(to_z, 0.5) + t.get("probability", 0.0) * 0.5
            assumptions.append("Incorporated empirical customer transition probabilities as baseline movement demand.")
        else:
            assumptions.append("Transition data insufficient (< 5 transitions); falling back to default category demand weights.")

        baseline_metrics = self._compute_layout_metrics(baseline, demand_weights, baseline_analytics)
        proposed_metrics = self._compute_layout_metrics(proposed, demand_weights, baseline_analytics)

        comparison, zone_comparisons = self._build_comparison(
            baseline_metrics,
            proposed_metrics,
            baseline_analytics,
            baseline,
            proposed
        )

        return {
            "model": "StorePulse AI Heuristic Layout Simulator v2",
            "is_synthetic": not used_empirical_transitions,
            "data_source": "EMPIRICAL_TRANSITIONS" if used_empirical_transitions else "HEURISTIC_SIMULATION",
            "disclaimer": (
                "All proposed values are heuristic estimates based on geometric "
                "layout analysis and observed flow patterns. They do NOT predict "
                "real customer behavior. Field validation is required before operational decisions."
            ),
            "assumptions": assumptions,
            "used_empirical_transitions": used_empirical_transitions,
            "baseline": {
                "layout_id": baseline.id,
                "layout_name": baseline.name,
                "metrics": baseline_metrics,
                "validation": self.validate_layout(baseline),
            },
            "proposed": {
                "layout_id": proposed.id,
                "layout_name": proposed.name,
                "metrics": proposed_metrics,
                "validation": self.validate_layout(proposed),
            },
            "comparison": comparison,
            "zone_comparisons": zone_comparisons,
            "generated_at": time.time(),
        }

    def _compute_layout_metrics(
        self,
        layout: LayoutConfig,
        demand_weights: Optional[Dict[str, float]] = None,
        real_analytics: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Compute geometric and zone metrics for a single layout."""
        weights = demand_weights or self.ZONE_DEMAND_WEIGHTS
        elements = layout.elements or []
        zones = layout.zones or []

        if not zones:
            try:
                from backend.zone_analytics import zone_analytics_engine
                configured_zones = zone_analytics_engine.get_zones()
                zones = [
                    {
                        "id": z.id,
                        "name": z.name,
                        "type": z.type,
                        "polygon": [{"x": p[0], "y": p[1]} for p in z.polygon],
                        "capacity": z.capacity,
                    }
                    for z in configured_zones
                ]
            except Exception:
                zones = []

        # Space utilization: fraction occupied by shelves/obstacles
        total_element_area = sum(
            self._norm_element(e)[2] * self._norm_element(e)[3]
            for e in elements
            if e.element_type not in ("entrance", "exit")
        )
        space_utilization = round(min(1.0, total_element_area) * 100, 1)
        free_space = round(max(0.0, 100.0 - space_utilization), 1)

        # Walking distance estimate: entrance to each zone centroid
        entrance = self._find_entrance(elements)
        zone_distances = {}
        zone_details = {}

        for zone in zones:
            zid = zone.get("id", "?")
            zname = zone.get("name", zid)
            ztype = zone.get("type", "display")
            zx, zy = self._zone_centroid(zone.get("polygon", []))
            dist = self._manhattan_distance(entrance, (zx, zy))
            demand = weights.get(ztype, weights.get(zid, 0.5))

            # Aisle clearance: distance from centroid to closest physical fixture
            clearance = self._estimate_zone_clearance(elements, (zx, zy))

            # Congestion risk heuristic based on clearance, distance, and density
            if clearance < 0.10:
                congestion_risk = "CRITICAL"
                risk_pct = 85.0
            elif clearance < 0.15:
                congestion_risk = "HIGH"
                risk_pct = 65.0
            elif clearance < 0.22:
                congestion_risk = "MEDIUM"
                risk_pct = 40.0
            else:
                congestion_risk = "LOW"
                risk_pct = 15.0

            # If real analytics exist for this zone, adjust baseline risk
            if real_analytics and zid in real_analytics:
                z_real = real_analytics[zid]
                if z_real.get("congestion_level") in ("HIGH", "CRITICAL"):
                    risk_pct = min(100.0, risk_pct + 15.0)

            zone_distances[zid] = {
                "distance_units": round(dist, 3),
                "demand_weight": round(demand, 2),
                "weighted_distance": round(dist * demand, 3),
            }
            zone_details[zid] = {
                "zone_id": zid,
                "zone_name": zname,
                "zone_type": ztype,
                "distance": round(dist, 3),
                "aisle_clearance": round(clearance, 3),
                "congestion_risk": congestion_risk,
                "congestion_risk_pct": round(risk_pct, 1),
            }

        avg_weighted_dist = (
            sum(v["weighted_distance"] for v in zone_distances.values()) / max(len(zone_distances), 1)
        )

        # Route conflict score: overlapping elements reduce walkability
        conflict_score = self._estimate_conflicts(elements)

        # Checkout accessibility
        checkout_dist = self._checkout_distance(elements, zones, entrance)

        # Overall estimated layout friction (0-100 heuristic decision index)
        occ_penalty = max(0.0, (space_utilization - 25.0) * 1.5)
        dist_penalty = min(50.0, checkout_dist * 50.0)
        est_friction = round(min(100.0, max(0.0, conflict_score * 0.4 + occ_penalty * 0.35 + dist_penalty * 0.25)), 1)

        # Bottleneck risk index (composite across zone risks and conflicts)
        avg_risk = sum(z["congestion_risk_pct"] for z in zone_details.values()) / max(len(zone_details), 1) if zone_details else 20.0
        bottleneck_index = round(min(100.0, avg_risk * 0.6 + conflict_score * 0.4), 1)

        return {
            "space_utilization_pct": space_utilization,
            "free_space_pct": free_space,
            "element_count": len(elements),
            "zone_count": len(zones),
            "avg_weighted_walking_distance": round(avg_weighted_dist, 3),
            "checkout_distance": round(checkout_dist, 3),
            "route_conflict_score": round(conflict_score, 1),
            "estimated_layout_friction": est_friction,
            "bottleneck_risk_index": bottleneck_index,
            "zone_distances": zone_distances,
            "zone_details": zone_details,
        }

    def _estimate_zone_clearance(self, elements: List[ShelfElement], centroid: Tuple[float, float]) -> float:
        """Estimate minimum distance from a zone centroid to any physical obstacle."""
        physical_elements = [e for e in elements if e.element_type not in ("entrance", "exit")]
        if not physical_elements:
            return 0.5
        min_dist = 1.0
        zx, zy = centroid
        for e in physical_elements:
            ex, ey, ew, eh = self._norm_element(e)
            ecx, ecy = ex + ew / 2.0, ey + eh / 2.0
            dist = math.hypot(zx - ecx, zy - ecy)
            if dist < min_dist:
                min_dist = dist
        return min_dist

    def _build_comparison(
        self,
        baseline: Dict,
        proposed: Dict,
        real_analytics: Optional[Dict],
        baseline_layout: LayoutConfig,
        proposed_layout: LayoutConfig,
    ) -> Tuple[List[Dict], List[Dict]]:
        """Build a row-by-row comparison table with mathematically safe zero-baseline handling."""
        rows = []

        def row(metric, b_val, p_val, unit="", lower_is_better=True):
            if isinstance(b_val, (int, float)) and isinstance(p_val, (int, float)):
                abs_diff = round(p_val - b_val, 3)
                if b_val != 0:
                    pct_diff = f"{round((abs_diff / float(b_val)) * 100, 1)}%"
                else:
                    pct_diff = "N/A (baseline is 0)" if abs_diff != 0 else "0.0%"
                better = (abs_diff < 0) if lower_is_better else (abs_diff > 0)
                direction = "BETTER" if better else ("SAME" if abs_diff == 0 else "WORSE")
            else:
                abs_diff = "N/A"
                pct_diff = "N/A"
                direction = "N/A"

            rows.append({
                "metric": metric,
                "baseline": f"{b_val}{unit}",
                "proposed": f"{p_val}{unit}",
                "absolute_diff": f"{abs_diff}{unit}" if abs_diff != "N/A" else "N/A",
                "pct_diff": pct_diff,
                "direction": direction,
                "source": "heuristic_estimate",
                "confidence": "MEDIUM",
            })

        row("Space Utilization", baseline["space_utilization_pct"], proposed["space_utilization_pct"], "%", lower_is_better=False)
        row("Free Walking Space", baseline["free_space_pct"], proposed["free_space_pct"], "%", lower_is_better=False)
        row("Avg Weighted Walking Distance", baseline["avg_weighted_walking_distance"], proposed["avg_weighted_walking_distance"], " units", lower_is_better=True)
        row("Checkout Accessibility Distance", baseline["checkout_distance"], proposed["checkout_distance"], " units", lower_is_better=True)
        row("Route Conflict Score", baseline["route_conflict_score"], proposed["route_conflict_score"], "", lower_is_better=True)
        row("Estimated Layout Flow Friction", baseline.get("estimated_layout_friction", 0.0), proposed.get("estimated_layout_friction", 0.0), "", lower_is_better=True)
        row("Predicted Bottleneck Risk Index", baseline.get("bottleneck_risk_index", 0.0), proposed.get("bottleneck_risk_index", 0.0), "", lower_is_better=True)
        row("Element Count", baseline["element_count"], proposed["element_count"], " items", lower_is_better=False)

        # Inject real analytics if available
        if real_analytics:
            for zone_id, zstats in real_analytics.items():
                rows.append({
                    "metric": f"[MEASURED] {zstats.get('zone_name', zone_id)} Avg Dwell",
                    "baseline": f"{zstats.get('avg_dwell_seconds', 0):.1f}s",
                    "proposed": "Requires physical trial",
                    "absolute_diff": "N/A",
                    "pct_diff": "N/A",
                    "direction": "N/A",
                    "source": "real_measurement",
                    "confidence": "HIGH" if zstats.get("sample_count", 0) >= 10 else "MEDIUM",
                })

        # Zone-by-zone comparison subtable
        zone_comparisons = []
        b_zones = baseline.get("zone_details", {})
        p_zones = proposed.get("zone_details", {})
        all_zids = set(b_zones.keys()).union(p_zones.keys())

        for zid in all_zids:
            bz = b_zones.get(zid, {})
            pz = p_zones.get(zid, {})
            zname = pz.get("zone_name") or bz.get("zone_name") or zid
            b_risk = bz.get("congestion_risk", "LOW")
            p_risk = pz.get("congestion_risk", "LOW")
            b_clear = bz.get("aisle_clearance", 0.5)
            p_clear = pz.get("aisle_clearance", 0.5)
            clear_diff = round(p_clear - b_clear, 3)

            zone_comparisons.append({
                "zone_id": zid,
                "zone_name": zname,
                "baseline_clearance": b_clear,
                "proposed_clearance": p_clear,
                "baseline_clearance_pct": round(b_clear * 100, 1),
                "proposed_clearance_pct": round(p_clear * 100, 1),
                "clearance_change": clear_diff,
                "baseline_risk": b_risk,
                "proposed_risk": p_risk,
                "risk_direction": "BETTER" if p_clear > b_clear else ("WORSE" if p_clear < b_clear else "SAME"),
                "risk_change": "BETTER" if p_clear > b_clear else ("WORSE" if p_clear < b_clear else "SAME"),
                "dwell_impact": (
                    "Increased browsing area (+0% bottleneck dwell)" if p_clear > b_clear
                    else ("Constricted aisle may increase congestion dwell (+10-15%)" if p_clear < b_clear
                    else "Neutral dwell impact")
                ),
                "estimated_dwell_impact": (
                    "Increased aisle clearance; fluid customer movement" if p_clear > b_clear
                    else ("Constricted aisle clearance may increase localized dwell & bottlenecks" if p_clear < b_clear
                    else "Neutral dwell impact: clearance preserved")
                ),
                "confidence": "MEDIUM",
            })

        return rows, zone_comparisons

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
        xs = []
        ys = []
        for p in polygon:
            if isinstance(p, dict):
                xs.append(float(p.get("x", 0.0)))
                ys.append(float(p.get("y", 0.0)))
            elif isinstance(p, (list, tuple)) and len(p) >= 2:
                xs.append(float(p[0]))
                ys.append(float(p[1]))
        if not xs or not ys:
            return (0.5, 0.5)
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


# ── Data store for layouts ─────────────────────────────────────────────


class LayoutStore:
    """
    Database-backed store for What-If layout configurations with in-memory caching.
    Ensures layout persistence across server restarts and cloud deployments.
    """

    def __init__(self):
        self._layouts: Dict[str, LayoutConfig] = {}
        self._baseline_id: Optional[str] = None
        self._init_defaults()
        self._load_from_database()

    def _default_baseline_config(self) -> LayoutConfig:
        return LayoutConfig(
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

    def _init_defaults(self):
        """Initialize in-memory baseline fallback."""
        baseline = self._default_baseline_config()
        self._layouts["baseline"] = baseline
        self._baseline_id = "baseline"

    def _load_from_database(self):
        """Load layouts from persistent database."""
        try:
            import json
            from backend.database.connection import get_db_context
            from backend.database.models import LayoutModel

            with get_db_context() as db:
                db_layouts = db.query(LayoutModel).all()
                if not db_layouts:
                    baseline = self._default_baseline_config()
                    self._persist_to_db(baseline)
                    return

                for row in db_layouts:
                    elements_raw = json.loads(row.elements_json or "[]")
                    zones_raw = json.loads(row.zones_json or "[]")
                    elements = [
                        ShelfElement(
                            id=e["id"],
                            element_type=e["element_type"],
                            x=e["x"],
                            y=e["y"],
                            width=e["width"],
                            height=e["height"],
                            rotation=e.get("rotation", 0.0),
                            label=e.get("label", "")
                        )
                        for e in elements_raw
                    ]
                    config = LayoutConfig(
                        id=row.id,
                        name=row.name,
                        description=row.description or "",
                        elements=elements,
                        zones=zones_raw,
                        is_baseline=bool(row.is_baseline),
                        created_at=row.created_at or time.time()
                    )
                    self._layouts[config.id] = config
                    if config.is_baseline:
                        self._baseline_id = config.id
        except Exception:
            pass

    def _persist_to_db(self, layout: LayoutConfig):
        """Helper to write or update LayoutModel in DB."""
        try:
            import json
            from backend.database.connection import get_db_context
            from backend.database.models import LayoutModel

            elements_dict = [
                {
                    "id": e.id,
                    "element_type": e.element_type,
                    "x": e.x,
                    "y": e.y,
                    "width": e.width,
                    "height": e.height,
                    "rotation": e.rotation,
                    "label": e.label,
                }
                for e in (layout.elements or [])
            ]

            with get_db_context() as db:
                if layout.is_baseline:
                    db.query(LayoutModel).filter(LayoutModel.id != layout.id).update({"is_baseline": False})

                existing = db.query(LayoutModel).filter(LayoutModel.id == layout.id).first()
                if existing:
                    existing.name = layout.name
                    existing.description = layout.description
                    existing.is_baseline = layout.is_baseline
                    existing.elements_json = json.dumps(elements_dict)
                    existing.zones_json = json.dumps(layout.zones or [])
                    existing.updated_at = time.time()
                else:
                    new_layout = LayoutModel(
                        id=layout.id,
                        name=layout.name,
                        description=layout.description,
                        is_baseline=layout.is_baseline,
                        elements_json=json.dumps(elements_dict),
                        zones_json=json.dumps(layout.zones or []),
                        created_at=layout.created_at or time.time(),
                        updated_at=time.time()
                    )
                    db.add(new_layout)
        except Exception:
            pass

    def save_layout(self, layout: LayoutConfig) -> LayoutConfig:
        self._layouts[layout.id] = layout
        if layout.is_baseline:
            self._baseline_id = layout.id
            for lid, l in self._layouts.items():
                if lid != layout.id:
                    l.is_baseline = False
        self._persist_to_db(layout)
        return layout

    def get_layout(self, layout_id: str) -> Optional[LayoutConfig]:
        if layout_id not in self._layouts:
            self._load_from_database()
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
        deleted = self._layouts.pop(layout_id, None) is not None
        if deleted:
            try:
                from backend.database.connection import get_db_context
                from backend.database.models import LayoutModel
                with get_db_context() as db:
                    row = db.query(LayoutModel).filter(LayoutModel.id == layout_id).first()
                    if row:
                        db.delete(row)
            except Exception:
                pass
        return deleted

    def get_baseline(self) -> Optional[LayoutConfig]:
        if not self._baseline_id or self._baseline_id not in self._layouts:
            self._load_from_database()
        return self._layouts.get(self._baseline_id)


# Singletons
layout_simulator = LayoutSimulator()
layout_store = LayoutStore()
