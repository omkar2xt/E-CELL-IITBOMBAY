# StorePulse AI — REST & WebSocket API Reference

**Document:** API Reference Specification  
**Author:** Omkar Gurav  
**Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator  
**Base URL:** `http://localhost:8000`  
**WebSocket URL:** `ws://localhost:8000/ws`  
**Interactive Docs:** `http://localhost:8000/docs`  
**Version:** 1.0.0  

---

## 1. Zone Analytics Endpoints (`/api/zones`)

### 1.1 List All Zones
- **Method:** `GET /api/zones/`
- **Response (200 OK):**
  ```json
  {
    "zones": [
      {
        "id": "entrance",
        "name": "Entrance",
        "type": "entrance",
        "polygon": [{"x": 0.0, "y": 0.6}, {"x": 0.2, "y": 0.6}, {"x": 0.2, "y": 1.0}, {"x": 0.0, "y": 1.0}],
        "capacity": 8,
        "dwell_alert_seconds": 60.0
      }
    ]
  }
  ```

### 1.2 Create or Replace Zone
- **Method:** `POST /api/zones/`
- **Request Body:**
  ```json
  {
    "id": "bakery",
    "name": "Fresh Bakery",
    "type": "display",
    "polygon": [{"x": 0.2, "y": 0.2}, {"x": 0.4, "y": 0.2}, {"x": 0.4, "y": 0.5}, {"x": 0.2, "y": 0.5}],
    "capacity": 6,
    "dwell_alert_seconds": 120.0
  }
  ```
- **Response (200 OK):** `{"status": "created", "zone": { ... }}`

### 1.3 Get Real-Time Zone Stats
- **Method:** `GET /api/zones/stats`
- **Description:** Returns active lingering dwell, completed visit statistics (mean, median, P90), and current occupancy.
- **Response (200 OK):**
  ```json
  {
    "zone_stats": {
      "grocery": {
        "zone_name": "Grocery & Produce",
        "current_occupancy": 3,
        "active_avg_dwell_seconds": 18.4,
        "active_max_dwell_seconds": 32.1,
        "avg_dwell_seconds": 45.2,
        "median_dwell_seconds": 41.0,
        "p90_dwell_seconds": 78.5,
        "total_entries": 42,
        "completed_visits": 39,
        "congestion_ratio": 0.15
      }
    }
  }
  ```

### 1.4 Get Explainable Bottlenecks
- **Method:** `GET /api/zones/bottlenecks`
- **Response (200 OK):**
  ```json
  {
    "status": "CONGESTED",
    "total_bottlenecks": 1,
    "active_bottlenecks": [
      {
        "zone_id": "checkout",
        "zone_name": "Checkout Counter",
        "severity": "HIGH",
        "congested_duration_seconds": 8.5,
        "evidence": [
          "Capacity exceeded: 6/5 (120%)",
          "Sustained for 8.5s (threshold: 4.0s)"
        ],
        "recommendation": "Deploy additional cashier to Checkout Counter (8.5s sustained load)."
      }
    ]
  }
  ```

### 1.5 Get Zone Transitions & Routing Matrix
- **Method:** `GET /api/zones/transitions`
- **Response (200 OK):**
  ```json
  {
    "transitions": [
      {
        "from_zone": "entrance",
        "to_zone": "grocery",
        "count": 14,
        "probability": 0.700
      }
    ],
    "matrix": {
      "entrance": {
        "grocery": {"count": 14, "probability": 0.700},
        "checkout": {"count": 6, "probability": 0.300}
      }
    },
    "zone_outflow": {"entrance": 20},
    "total_transitions": 20,
    "data_sufficient": true,
    "confidence": "HIGH"
  }
  ```

---

## 2. Layouts & Simulator Endpoints (`/api/layouts`)

### 2.1 List Layouts
- **Method:** `GET /api/layouts/`
- **Response (200 OK):** `{"layouts": [ { "id": "baseline", "name": "Current Layout", "is_baseline": true, ... } ]}`

### 2.2 Get Baseline Layout
- **Method:** `GET /api/layouts/baseline`
- **Response (200 OK):** `{"layout": { "id": "baseline", "elements": [ ... ], "zones": [ ... ] }}`

### 2.3 Save / Create Layout
- **Method:** `POST /api/layouts/`
- **Request Body:**
  ```json
  {
    "name": "Promotional Aisle Reconfiguration",
    "description": "Widened main corridor by shifting Shelf B",
    "elements": [
      {
        "id": "s1",
        "element_type": "shelf",
        "x": 0.25,
        "y": 0.10,
        "width": 0.10,
        "height": 0.30,
        "rotation": 0,
        "label": "Shelf A"
      }
    ],
    "zones": [],
    "is_baseline": false
  }
  ```
- **Response (200 OK):** `{"status": "created", "layout": { "id": "layout_abc123", ... }}`

### 2.4 Validate Layout Geometry
- **Method:** `POST /api/layouts/validate`
- **Description:** Verifies boundary containment and detects physical fixture collisions (AABB).
- **Response (200 OK):**
  ```json
  {
    "valid": true,
    "is_valid": true,
    "errors": [],
    "warnings": [
      "Detected 1 overlapping fixture pairs causing aisle obstruction."
    ],
    "overlap_pairs": [
      {
        "element_1": "s2",
        "label_1": "Shelf B",
        "element_2": "s3",
        "label_2": "Shelf C"
      }
    ],
    "overlap_count": 1
  }
  ```

### 2.5 Run Heuristic Layout Simulation
- **Method:** `POST /api/layouts/simulate`
- **Request Body:**
  ```json
  {
    "baseline_id": "baseline",
    "proposed_id": "layout_abc123"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "model": "StorePulse AI Heuristic Layout Simulator v2",
    "used_empirical_transitions": true,
    "transition_summary": {
      "total_transitions": 24,
      "routes_count": 6,
      "data_sufficient": true,
      "confidence": "HIGH"
    },
    "comparison": [
      {
        "metric": "Predicted Bottleneck Risk Index",
        "baseline": "38.5",
        "proposed": "29.2",
        "absolute_diff": "-9.3",
        "pct_diff": "-24.2%",
        "direction": "BETTER",
        "source": "heuristic_estimate",
        "confidence": "MEDIUM"
      }
    ],
    "zone_comparisons": [
      {
        "zone_id": "grocery",
        "zone_name": "Grocery & Produce",
        "baseline_clearance_pct": 18.5,
        "proposed_clearance_pct": 24.0,
        "baseline_risk": "MEDIUM",
        "proposed_risk": "LOW",
        "risk_change": "BETTER",
        "estimated_dwell_impact": "Increased aisle clearance; fluid customer movement",
        "confidence": "MEDIUM"
      }
    ]
  }
  ```

---

## 3. Real-Time Streaming Endpoints

### 3.1 WebSocket Telemetry (`ws://localhost:8000/ws`)
- **Transport:** WebSocket text frames (JSON).
- **Broadcast Interval:** Every 5 frames (~150ms).
- **Payload Schema:**
  ```json
  {
    "timestamp": 1729340000.125,
    "frame_id": 1240,
    "count_in": 84,
    "count_out": 76,
    "occupancy": 8,
    "queue_count": 2,
    "queue_alert": false,
    "fps": 8.3,
    "tracked_count": 8,
    "is_demo": false,
    "source_type": "file",
    "connection_status": "connected",
    "zone_stats": { ... },
    "bottlenecks": { ... }
  }
  ```

### 3.2 MJPEG Video Stream (`GET /snapshot`)
- **Format:** Multipart JPEG (`multipart/x-mixed-replace; boundary=frame`).
- **Throttling:** ~15 FPS image delivery.
- **Embed Syntax:** `<img src="http://localhost:8000/snapshot" />`.
