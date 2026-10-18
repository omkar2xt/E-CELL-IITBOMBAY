# StorePulse AI — Retail Intelligence Dashboard

**Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator  
**Developer:** Omkar Gurav  
**Tech Stack:** React 19, Vite, React Router v7, Recharts, Lucide Icons  

---

## Overview

The StorePulse AI Dashboard provides 10 integrated retail operational views:

1. **Overview (`/`)** — Real-time entrance/exit counts, current occupancy, queue metrics, live camera stream, and zone density status.
2. **Live Analytics (`/live`)** — High-frequency telemetry (FPS, frame count, active tracks, queue history).
3. **Zone Analytics (`/zones`)** — Dwell times (average, median, maximum), occupancy distributions, and congestion alerts across defined polygon store zones.
4. **Movement Flow (`/movement`)** — Anonymized zone-to-zone transitions and popular shopping pathways.
5. **Heatmaps (`/heatmaps`)** — Foot-traffic density maps with color intensity overlays and snapshot downloads.
6. **Queue Monitoring (`/queue`)** — Checkout area queue length tracking, wait trends, and threshold alerts.
7. **Flow Friction (`/friction`)** — Multi-factor Flow Friction Scores (0–100) per zone with actionable operational recommendations.
8. **What-If Simulator (`/simulator`)** — Signature interactive SVG floor-plan canvas editor (drag, resize, rotate, add, and delete virtual shelves and obstacles).
9. **Scenario Comparison (`/comparison`)** — Metric-by-metric comparison between baseline and proposed store layouts.
10. **Settings & Privacy (`/settings`)** — Data retention policies, privacy controls, zone presets, and threshold calibration.

---

## Getting Started

### Development
```bash
npm install
npm run dev
```
The dashboard runs at `http://localhost:5173`.

### Production Build
```bash
npm run build
```
Generates production-optimized static assets in `dist/`.
