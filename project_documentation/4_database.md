# StorePulse AI — Data Storage & Schema Design

**Document:** Data Storage & Schema Design  
**Author:** Omkar Gurav  
**Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator  
**Version:** 1.0.0  

---

## 1. Storage Architecture Overview

StorePulse AI utilizes a high-throughput, low-latency in-memory data store designed specifically for real-time edge computer vision telemetry and interactive simulation. This architecture avoids database I/O bottlenecks during 30 FPS inference while maintaining complete schema validation and privacy-by-design data purging.

```
┌─────────────────────────────────────────────────────────────┐
│ Fast In-Memory State Layer (RAM / Thread-Safe Locks)        │
├──────────────────────────────┬──────────────────────────────┤
│ Zone Analytics Engine        │ Layout Store                 │
│ • Active Visits Map          │ • Baseline Layout Config     │
│ • Completed Visit Buffer     │ • Proposed Scenarios Map     │
│ • Zone Transition Matrix     │ • Fixture Geometry Store     │
│ • Bottleneck State Machine   │ • Validation Result Cache    │
└──────────────────────────────┴──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Production Relational / Time-Series Roadmap                 │
│ • PostgreSQL (Store Layouts, Zone Polygons, User Settings)  │
│ • TimescaleDB (Aggregated Dwell & Transition Telemetry)     │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Core Data Models & Schemas

### 2.1 Zone Configuration Schema (`Zone`)

```python
@dataclass
class Zone:
    id: str                                  # Unique zone slug (e.g. "grocery")
    name: str                                # Display title (e.g. "Grocery & Produce")
    type: str                                # "entrance", "checkout", "display", "grocery", "electronics", "promo"
    polygon: List[Tuple[float, float]]       # Normalized vertices [(x1, y1), (x2, y2), ...] where 0.0 <= x, y <= 1.0
    capacity: int = 10                       # Maximum recommended customer occupancy
    dwell_alert_seconds: float = 120.0       # Threshold for excessive linger alert
    color: Tuple[int, int, int] = (50, 200, 50) # BGR visualization color
```

---

### 2.2 Dwell Visit Tracking Record (`DwellRecord`)

```python
@dataclass
class DwellRecord:
    track_id: int                            # Temporary ByteTrack integer ID
    zone_id: str                             # Target zone identifier
    enter_time: float                        # Deterministic timestamp of entry (seconds)
    last_seen_time: float = 0.0              # Most recent detection timestamp
    exit_time: Optional[float] = None        # Finalized exit timestamp
    interrupted: bool = False                # True if finalized due to occlusion/timeout
    long_dwell_flagged: bool = False         # True if dwell > dwell_alert_seconds

    def dwell_seconds(self, now: float) -> float:
        end = self.exit_time if self.exit_time is not None else now
        return min(max(0.0, end - self.enter_time), 86400.0)
```

---

### 2.3 Bottleneck State Machine Record (`BottleneckState`)

```python
@dataclass
class BottleneckState:
    is_bottleneck: bool = False
    severity: str = "LOW"                    # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    first_congested_time: Optional[float] = None
    last_congested_time: Optional[float] = None
    congested_duration: float = 0.0
    evidence: List[str] = field(default_factory=list)
    recommendation: str = "Flow is normal."
    alert_start_time: Optional[float] = None
```

---

### 2.4 Transition Matrix Data Structure

```python
# Raw Transition Counter
_transitions: Dict[Tuple[str, str], int] = defaultdict(int)
# Example: {("entrance", "grocery"): 14, ("grocery", "checkout"): 10}

# Normalized Response Schema
{
    "transitions": [
        {
            "from_zone": "entrance",
            "to_zone": "grocery",
            "count": 14,
            "probability": 0.700            # P(grocery | entrance)
        }
    ],
    "matrix": {
        "entrance": {
            "grocery": {"count": 14, "probability": 0.700},
            "checkout": {"count": 6, "probability": 0.300}
        }
    },
    "zone_outflow": {"entrance": 20, "grocery": 10},
    "total_transitions": 30,
    "data_sufficient": True,                 # True if total_transitions >= 5
    "confidence": "HIGH"                     # "HIGH" (>= 20), "MEDIUM" (>= 5), "LOW" (< 5)
}
```

---

### 2.5 Floor Plan Layout Schema (`LayoutConfig`)

```python
@dataclass
class ShelfElement:
    id: str                                  # Element ID (e.g. "s1", "c1")
    element_type: str                        # "shelf", "checkout", "display", "entrance", "exit", "obstacle"
    x: float                                 # Normalized or pixel X coordinate
    y: float                                 # Normalized or pixel Y coordinate
    width: float                             # Width
    height: float                            # Height
    rotation: int = 0                        # Rotation degrees (0, 90, 180, 270)
    label: str = ""                          # Human-readable title (e.g. "Shelf A")

@dataclass
class LayoutConfig:
    id: str
    name: str
    description: str = ""
    elements: List[ShelfElement] = field(default_factory=list)
    zones: List[Dict] = field(default_factory=list)
    is_baseline: bool = False
    created_at: float = field(default_factory=time.time)
```

---

## 3. Data Retention & Privacy Purge Policies

1. **Transient Tracking States:**
   - Active tracking entries (`_active`) are finalized upon zone exit or purged after $5.0\text{s}$ of camera absence.
   - Completed visit histories (`_completed`) are capped using a FIFO circular buffer of 1,000 entries per zone.
2. **Zero Biometric Identity Storage:**
   - No customer biometric profiles, face embeddings, or personal identifiers are stored.
   - Integer tracking IDs (`1, 2, 3...`) are purely local and reused upon reset.
3. **No Raw Video Disk Persistence:**
   - Video frames exist solely in volatile memory buffers (`latest_frame`) and are overwritten every frame cycle.

---

## 4. Production Database Migration Roadmap

For long-term multi-store enterprise deployments, the in-memory store interfaces can map to:
- **PostgreSQL 16:**
  - `stores` (Store metadata, dimensions, camera configs)
  - `layouts` (JSONB fixture layout geometries)
  - `zones` (PostGIS spatial polygons)
- **TimescaleDB:**
  - `hourly_zone_dwell` (Continuous aggregates of median and P90 dwell times)
  - `zone_transitions` (Hypertable tracking 15-minute aggregated routing probabilities)
