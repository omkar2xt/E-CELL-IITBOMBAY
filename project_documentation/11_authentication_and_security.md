# StorePulse AI — Security, Privacy by Design & Authentication

**Document:** Security & Privacy by Design Specification  
**Author:** Omkar Gurav  
**Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator  
**Version:** 1.0.0  

---

## 1. Privacy by Design Manifesto

Physical retail surveillance systems often cross ethical and regulatory lines by implementing persistent identity tracking, facial recognition, or unauthorized biometric profiling.

**StorePulse AI** was engineered from day one under a strict **Privacy by Design** framework compliant with the General Data Protection Regulation (GDPR), California Consumer Privacy Act (CCPA), and the European Union Artificial Intelligence Act (EU AI Act):

```
┌─────────────────────────────────────────────────────────────┐
│ Core Privacy Guarantees                                     │
├─────────────────────────────────────────────────────────────┤
│ 1. Zero Facial Recognition & Biometric Embeddings          │
│ 2. Ephemeral In-Memory Tracking IDs (RAM-Only)              │
│ 3. Zero Persistent Video Storage (Frames Analyzed & Purged) │
│ 4. Aggregate Spatial Telemetry Only                         │
│ 5. Strict Demographics Disable by Default                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Technical Privacy Implementations

### 2.1 Zero Biometrics & Facial Feature Elimination
- The computer vision detector strictly filters detections to COCO Class 0 (`person`) full-body bounding boxes.
- No facial landmark extraction, facial embeddings, retina scanning, or gait recognition algorithms exist in the active codebase.
- Demographics estimation (`DEMOGRAPHICS_ENABLED=false`) is explicitly disabled in the default production configuration.

### 2.2 Ephemeral Integer Tracking IDs
- The ByteTrack tracker assigns arbitrary, localized integers (`Track 1, Track 2, Track 3...`).
- These IDs exist exclusively in volatile RAM during active camera visibility.
- When an individual leaves the store, their track state is purged from memory after 60 frames (~2.0 seconds).
- IDs are completely recycled upon application restart, preventing persistent customer tracking across days or store visits.

### 2.3 Zero Raw Video Storage Policy
- Video frames captured via OpenCV `VideoCapture` are processed in-memory as NumPy arrays.
- Frames are never written to disk, cached to temporary folders, or uploaded to third-party cloud servers.
- The `/snapshot` MJPEG endpoint streams frames directly from volatile RAM buffers (`latest_frame`) with no disk buffering.

### 2.4 Aggregate Spatial Telemetry
- All stored analytics—such as zone dwell times, line crossings, Flow Friction scores, and transition matrices—are stored purely as aggregated statistical distributions (mean, median, P90, count).
- Individual customer trajectories cannot be reconstructed from saved historical metrics.

---

## 3. Network & Application Security

### 3.1 REST API Security & Defensive Input Validation
- **Pydantic Model Encoders:** All incoming HTTP request payloads (`ZoneCreateRequest`, `LayoutCreateRequest`, `SimulationRequest`) are strictly validated for type safety, missing fields, and coordinate ranges.
- **Boundary Clamping:** Point coordinates are validated to ensure polygons contain at least 3 vertices and dimensions are strictly positive ($W > 0, H > 0$).
- **CORS Restrictions:** Configurable via FastAPI middleware. In enterprise deployments, `allow_origins` is restricted to authorized operations domain origins.

### 3.2 WebSocket Security & Reconnection
- **Endpoint:** `ws://localhost:8000/ws`.
- **Disconnect Resilience:** Disconnections trigger safe cleanup in `ConnectionManager` without server crashes or zombie connections.
- **Production Roadmap:** Token-based authentication using short-lived JWT tokens passed in the WebSocket connection header (`Authorization: Bearer <token>`).

### 3.3 Camera Feed & Credential Security
- RTSP camera URLs containing authentication credentials (e.g. `rtsp://user:pass@camera_ip:554`) are encapsulated in server-side configuration (`.env`).
- Credentials are never logged to console output, broadcast over WebSockets, or exposed in frontend client bundles.
- TLS/SSL encryption is supported for secure RTSP (`rtsps://`) and HTTPS feeds.
