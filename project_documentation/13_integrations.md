# StorePulse AI — Enterprise & Hardware Integrations Specification

**Document Version:** 1.0.0  
**Author:** Omkar Gurav  
**Status:** Verified Production Architecture  

---

## 1. Overview

StorePulse AI connects edge computer vision with existing retail infrastructure. The system is engineered to integrate across five distinct layers:
1. **Video Ingestion:** IP cameras (RTSP / ONVIF), USB webcams, recorded MP4/MKV video files, and synthetic frame generators.
2. **Point of Sale (POS) Systems:** Cash register transaction streams for dwell-to-purchase conversion calculation.
3. **IoT & Sensor Brokers (MQTT / Webhooks):** Real-time pub/sub delivery of occupancy alerts to electronic shelf labels, smart lighting, and staff pagers.
4. **Enterprise Resource Planning (ERP):** Staff scheduling and inventory replenishment based on zone dwell trends.
5. **Monitoring & Telemetry:** Prometheus metrics, Grafana dashboards, and CSV/JSON reporting endpoints.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        STORE ENVIRONMENT SENSORS                       │
│  [RTSP/ONVIF CCTV]    [USB Webcams]    [POS Cash Registers]    [MQTT] │
└──────────┬──────────────────┬───────────────────┬────────────────┬─────┘
           │                  │                   │                │
           ▼                  ▼                   ▼                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     STOREPULSE AI PROCESSING CORE                      │
│   • Video Pipeline (OpenCV VideoCapture / Threaded Async Buffer)      │
│   • YOLO11n Object Detection + ByteTrack Association Engine            │
│   • Zone Analytics & Dwell Time Aggregator                             │
│   • Correlation Engine (Dwell Time vs. POS Receipt Timestamps)         │
└──────────┬──────────────────┬───────────────────┬──────────────────────┘
           │                  │                   │
           ▼                  ▼                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         ENTERPRISE CONSUMERS                           │
│  [StorePulse Dashboard]  [ERP Workforce API]  [Smart Pager Alerts]     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Video Stream Ingestion (CV Layer)

The ingestion engine is encapsulated in `backend/pipeline.py` with multi-source fallback support:

### 2.1 Supported Ingestion Sources

| Source Type | Protocol / URI | Configuration Parameter | Typical Latency | Reconnection Strategy |
|:---|:---|:---|:---:|:---|
| **IP Security Cameras** | RTSP / ONVIF (`rtsp://user:pass@ip:554/live`) | `VIDEO_SOURCE="rtsp://..."` | 150–300 ms | Auto-reconnect with exponential backoff (1s to 30s) |
| **Local USB Webcams** | DirectShow / V4L2 (`0`, `1`, `/dev/video0`) | `VIDEO_SOURCE=0` | < 30 ms | Auto-reopen on device plug/unplug event |
| **Synthetic Video File** | MP4 / AVI / MKV local filesystem path | `VIDEO_SOURCE="data/retail_demo.mp4"` | 0 ms (Realtime synced) | Automatic loop mode (`cap.set(CAP_PROP_POS_FRAMES, 0)`) |
| **Synthetic Mock Stream** | NumPy procedural test pattern | `--mock-stream` CLI flag | 0 ms | Generated at exact requested FPS (e.g., 30 FPS) |

### 2.2 RTSP Camera Configuration Example

```python
# backend/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    VIDEO_SOURCE: str = "rtsp://admin:SecurityPass123@192.168.1.120:554/stream1"
    TARGET_FPS: int = 15
    FRAME_SKIP: int = 2  # Inference every 2nd frame to save edge CPU
    RTSP_TRANSPORT: str = "tcp"  # TCP prevents UDP packet drops in retail environments

    class Config:
        env_file = ".env"
```

### 2.3 Frame Buffer & Threading Architecture

To guarantee the computer vision model never blocks camera RTSP buffers (which causes RTSP feed drift or frame corruption), ingestion runs on an isolated daemon thread:

```python
class ThreadedVideoCapture:
    def __init__(self, src: str):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Only keep freshest frame
        self.lock = threading.Lock()
        self.frame = None
        self.running = True
        self.thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.thread.start()

    def _reader_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            with self.lock:
                self.frame = frame

    def read(self):
        with self.lock:
            return self.frame is not None, self.frame.copy() if self.frame is not None else None
```

---

## 3. Point of Sale (POS) Register Integration

### 3.1 Dwell-to-Purchase Conversion Correlation

A high dwell time in a merchandise zone can indicate high customer interest or extreme confusion. By correlating zone dwell time with downstream checkout transactions, StorePulse calculates **True Merchandise Conversion**:

$$\text{Zone Conversion Rate} = \frac{\text{Transactions containing items from Zone } z \text{ within window } \Delta t}{\text{Unique Visitor Visits to Zone } z \text{ within window } \Delta t}$$

### 3.2 POS Webhook Ingestion Endpoint

StorePulse exposes `/api/integrations/pos/transaction` to ingest live receipts:

```http
POST /api/integrations/pos/transaction HTTP/1.1
Content-Type: application/json

{
  "register_id": "POS_04",
  "cashier_id": "EMP_8921",
  "timestamp": "2026-10-19T18:04:12Z",
  "items": [
    {"sku": "SKU_44910", "zone_category": "promo_display", "amount": 29.99},
    {"sku": "SKU_10022", "zone_category": "aisle_1", "amount": 4.50}
  ],
  "total_amount": 34.49,
  "queue_duration_seconds": 58.0
}
```

### 3.3 Cashier Queue Calibration

POS transaction completion timestamps directly calibrate the automated queue monitor (`analytics/queue_monitor.py`):
- When a POS transaction completes, the queue length is validated against visual bounding box counts.
- Cashier service duration is tracked dynamically, refining the **Predicted Queue Wait Time**:

$$\widehat{T}_{\text{wait}} = N_{\text{queue}} \times \overline{T}_{\text{service}}$$

---

## 4. IoT & MQTT Telemetry Broker

StorePulse AI includes an optional lightweight MQTT publisher (`integrations/mqtt_client.py`) for smart store automation.

### 4.1 Topic Hierarchy

| MQTT Topic | Payload Type | Description |
|:---|:---|:---|
| `storepulse/{store_id}/occupancy` | JSON | Live store customer count broadcast every 2 seconds. |
| `storepulse/{store_id}/bottleneck/alert` | JSON | Triggered immediately when a zone enters critical bottleneck state. |
| `storepulse/{store_id}/zone/{zone_id}` | JSON | Individual zone occupancy and average dwell duration. |

### 4.2 Sample Alert Payload

```json
{
  "event": "BOTTLENECK_CRITICAL",
  "zone_id": "checkout_counter",
  "severity": "CRITICAL",
  "current_occupancy": 6,
  "threshold_dwell_seconds": 45.0,
  "measured_avg_dwell_seconds": 78.5,
  "recommended_action": "DISPATCH_ASSIST_REGISTER"
}
```

### 4.3 Triggered Actions

1. **Staff Paging:** Store manager Apple Watch / Android pager triggers haptic alerts when queue dwell exceeds 90 seconds.
2. **Dynamic Digital Signage:** Overhead monitors redirect foot traffic from congested `aisle_1` to open `aisle_2`.
3. **Smart Lighting:** Subtle shelf-lighting shifts highlight promotional displays when footfall slows down.

---

## 5. ERP & Workforce Management Integration

### 5.1 Dynamic Cashier Scheduling

StorePulse AI provides an export API (`/api/analytics/export/staffing_needs`) consumed by workforce scheduling platforms (e.g., SAP SuccessFactors, Workday, Deputy):

```json
{
  "forecast_window": "2026-10-19T19:00:00Z - 2026-10-19T20:00:00Z",
  "predicted_peak_dwell_zone": "checkout_counter",
  "recommended_registers_open": 3,
  "current_registers_active": 1,
  "justification": "Historical Markov transition from promo_display to checkout predicts +65% checkout influx in 15 minutes."
}
```

---

## 6. Enterprise Monitoring & Observability

### 6.1 Prometheus Metrics Endpoint (`/metrics`)

StorePulse AI exports real-time Prometheus gauges:

```prometheus
# HELP storepulse_active_visitors Total count of actively tracked people in camera view
# TYPE storepulse_active_visitors gauge
storepulse_active_visitors 14

# HELP storepulse_zone_dwell_seconds Average dwell time per store zone
# TYPE storepulse_zone_dwell_seconds gauge
storepulse_zone_dwell_seconds{zone="entrance"} 4.2
storepulse_zone_dwell_seconds{zone="aisle_1"} 22.8
storepulse_zone_dwell_seconds{zone="promo_display"} 38.6
storepulse_zone_dwell_seconds{zone="checkout_counter"} 68.4

# HELP storepulse_inference_latency_ms CV model inference duration in milliseconds
# TYPE storepulse_inference_latency_ms gauge
storepulse_inference_latency_ms 18.4
```

### 6.2 Grafana Dashboard Integration

Prometheus metrics can be loaded directly into Grafana with the pre-built template in `deploy/grafana/storepulse_dashboard.json`:
- Panel 1: Live Occupancy & Entrances (Gauge & Time Series)
- Panel 2: Zone Dwell Heatmap (Bar Gauge)
- Panel 3: Active Bottleneck Incidents (Alert Status Map)
- Panel 4: Camera Pipeline FPS & Inference Latency (Graph)

---

## 7. Data Export Endpoints

To support downstream business intelligence (PowerBI, Tableau, Google Looker), StorePulse provides raw and aggregated data export endpoints:

| Endpoint | Method | Format | Description |
|:---|:---:|:---:|:---|
| `/api/analytics/export/dwell.csv` | GET | CSV | Tabular record of all completed visitor dwell sessions with timestamps and durations. |
| `/api/analytics/export/transitions.json` | GET | JSON | Complete directed graph of customer transitions between zones. |
| `/api/analytics/export/friction_audit.json` | GET | JSON | Comprehensive friction audit report including friction scores, density ratios, and bottleneck histories. |
