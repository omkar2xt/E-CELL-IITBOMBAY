# StorePulse AI — API Documentation
**Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator  
**Developer:** Omkar Gurav  
**Version:** 1.0.0  

All REST endpoints return JSON payloads unless specified otherwise (such as the MJPEG stream). Base URL: `http://localhost:8000`

---

## 1. System & Health

### `GET /health`
Returns system status, product branding, and version.
**Response:**
```json
{
  "status": "ok",
  "product": "StorePulse AI",
  "version": "1.0.0",
  "developer": "Omkar Gurav"
}
```

### `GET /snapshot`
Streams real-time MJPEG frames processed with heatmaps, zone overlays, counting line, and StorePulse AI branding.
- **Media Type:** `multipart/x-mixed-replace; boundary=frame`

### `WebSocket /ws`
Real-time JSON metrics broadcast emitted every $N$ frames (default every 5 frames).
**Message Payload:**
```json
{
  "timestamp": 1729224000.12,
  "frame_id": 1420,
  "count_in": 45,
  "count_out": 38,
  "occupancy": 7,
  "queue_count": 2,
  "queue_alert": false,
  "fps": 28.4,
  "tracked_count": 8,
  "demographics": {
    "enabled": false,
    "sample_count": 0,
    "gender_distribution": {},
    "age_distribution": {}
  },
  "zone_stats": {
    "checkout": {
      "current_occupancy": 2,
      "avg_dwell_seconds": 45.2,
      "congestion_status": "LOW"
    }
  }
}
```

---

## 2. Analytics Endpoints (`/api/analytics`)

### `GET /api/analytics/status`
Returns background pipeline running state.
**Response:**
```json
{
  "pipeline_running": true,
  "status": "running",
  "product": "StorePulse AI",
  "version": "1.0.0"
}
```

### `GET /api/analytics/metrics`
Returns current instantaneous metrics snapshot.

### `GET /api/analytics/zones`
Returns comprehensive zone statistics including occupancy, dwell times (average, median, maximum), sample counts, and congestion levels.
**Response:**
```json
{
  "zone_analytics": {
    "entrance": {
      "zone_id": "entrance",
      "zone_name": "Entrance",
      "zone_type": "entrance",
      "current_occupancy": 1,
      "capacity": 8,
      "total_entries": 32,
      "avg_dwell_seconds": 18.5,
      "median_dwell_seconds": 16.0,
      "max_dwell_seconds": 42.0,
      "congestion_pct": 12.5,
      "congestion_status": "LOW",
      "dwell_alert": false,
      "sample_count": 28
    }
  }
}
```

### `GET /api/analytics/friction`
Calculates explainable Flow Friction Scores (0–100) per zone and store-wide.
**Response:**
```json
{
  "zone_scores": {
    "checkout": {
      "zone_id": "checkout",
      "zone_name": "Checkout",
      "score": 38.5,
      "alert_level": "LOW",
      "components": {
        "occupancy_score": 40.0,
        "dwell_score": 35.0,
        "queue_score": 66.7,
        "weights": { "occupancy": 0.35, "dwell": 0.35, "queue": 0.30 }
      },
      "explanation": "Flow is smooth",
      "recommendation": "No action needed. Zone is operating normally.",
      "data_confidence": "HIGH"
    }
  },
  "store_level": {
    "score": 34.2,
    "peak_score": 52.0,
    "alert_level": "MEDIUM",
    "status": "CAUTION",
    "high_friction_zones": []
  },
  "disclaimer": "Prototype heuristic metric. Not a validated industry standard."
}
```

### `GET /api/analytics/movement`
Returns aggregated zone-to-zone customer transitions.
**Response:**
```json
{
  "transitions": [
    { "from_zone": "entrance", "to_zone": "grocery", "count": 18 },
    { "from_zone": "grocery", "to_zone": "checkout", "count": 14 }
  ]
}
```

---

## 3. Zone Configuration Endpoints (`/api/zones`)

### `GET /api/zones/`
List all configured zones.

### `POST /api/zones/`
Create or update a polygon zone.
**Request:**
```json
{
  "id": "electronics",
  "name": "Electronics & Gadgets",
  "type": "electronics",
  "polygon": [
    { "x": 0.55, "y": 0.1 },
    { "x": 0.9, "y": 0.1 },
    { "x": 0.9, "y": 0.45 },
    { "x": 0.55, "y": 0.45 }
  ],
  "capacity": 12,
  "dwell_alert_seconds": 300.0
}
```

### `DELETE /api/zones/{zone_id}`
Delete a zone by ID.

### `POST /api/zones/reset`
Reset dwell records and transition counters.

### `POST /api/zones/defaults`
Reload the standard retail zone defaults.

---

## 4. What-If Layout Simulator Endpoints (`/api/layouts`)

### `GET /api/layouts/`
List all saved floor plans (baseline and proposed).

### `GET /api/layouts/baseline`
Retrieve the baseline store layout.

### `POST /api/layouts/`
Save a new layout configuration.
**Request:**
```json
{
  "id": "proposed_wide_aisles",
  "name": "Wide Aisle Layout",
  "description": "Widened central thoroughfare to reduce bottleneck",
  "elements": [
    {
      "id": "shelf_1",
      "element_type": "shelf",
      "x": 150.0,
      "y": 120.0,
      "width": 100.0,
      "height": 40.0,
      "rotation": 0.0,
      "label": "Gourmet Snacks"
    }
  ],
  "zones": [],
  "is_baseline": false
}
```

### `POST /api/layouts/simulate`
Run heuristic simulation comparing baseline layout to proposed layout.
**Request:**
```json
{
  "baseline_id": "baseline",
  "proposed_id": "proposed_wide_aisles"
}
```
**Response:**
```json
{
  "model": "StorePulse AI Heuristic Layout Simulator v1",
  "disclaimer": "All proposed values are heuristic estimates based on geometric layout analysis.",
  "assumptions": [
    "Customer traffic is assumed proportional to zone demand weights",
    "Walking distance is approximated as Manhattan distance between zones",
    "Obstacle density reduces available path space linearly"
  ],
  "baseline": {
    "layout_id": "baseline",
    "metrics": {
      "space_utilization_pct": 31.7,
      "free_space_pct": 68.3,
      "avg_weighted_walking_distance": 0.485,
      "route_conflict_score": 0.0
    }
  },
  "proposed": {
    "layout_id": "proposed_wide_aisles",
    "metrics": {
      "space_utilization_pct": 28.5,
      "free_space_pct": 71.5,
      "avg_weighted_walking_distance": 0.442,
      "route_conflict_score": 0.0
    }
  },
  "comparison": [
    {
      "metric": "Free Walking Space",
      "baseline": "68.3%",
      "proposed": "71.5%",
      "absolute_diff": "3.2%",
      "pct_diff": "4.7%",
      "direction": "BETTER",
      "source": "heuristic_estimate",
      "confidence": "LOW"
    }
  ]
}
```
