# StorePulse AI — System & UI/UX Design Specification

**Document:** System & UI/UX Design  
**Author:** Omkar Gurav  
**Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator  
**Version:** 1.0.0  

---

## 1. Design Philosophy & Aesthetic Principles

StorePulse AI was designed to meet enterprise operations standards while delivering an executive-grade aesthetic. The user experience is built on four core design tenets:

1. **Immediate Clarity Over Clutter:** High-density spatial and temporal metrics are structured into modular cards, color-coded badges, and intuitive visual hierarchies.
2. **Glassmorphism & Sleek Dark Mode:** Tailored dark navy/slate palette (`#060b18` to `#111827`) reduces eye fatigue during extended operations shifts and makes color-coded heatmaps and alerts stand out.
3. **Transparent Scientific Labeling:** Every data element is explicitly labeled as either `[MEASURED REAL OBSERVED EVENTS]` or `[HEURISTIC ESTIMATE]` to eliminate ambiguity.
4. **Fluid Spatial Interactivity:** The What-If Layout editor uses high-performance SVG with real-time collision feedback, magnetic snap-to-grid alignment, and instant visual validation.

---

## 2. Design System Tokens & Color Palette

### 2.1 CSS Variables & Palette (`dashboard/src/index.css`)

```css
:root {
  /* Brand Accents */
  --brand-primary:      #6366f1;   /* Indigo - Primary actions & links */
  --brand-primary-dark: #4f46e5;
  --brand-accent:       #06b6d4;   /* Cyan - Active selections & metrics */
  --brand-accent-dark:  #0891b2;
  --brand-gold:         #f59e0b;   /* Amber - Warnings & attention */
  --brand-success:      #10b981;   /* Emerald - Normal status & better trends */
  --brand-danger:       #ef4444;   /* Red - Bottlenecks & collisions */
  --brand-purple:       #8b5cf6;   /* Violet - Promo displays & electronics */

  /* Background Hierarchy */
  --bg-base:            #060b18;   /* Deepest Navy canvas */
  --bg-surface:         #0d1526;   /* Sidebar & header surfaces */
  --bg-card:            #111827;   /* Modular card background */
  --bg-card-hover:      #1a2540;   /* Interactive card hover */
  --bg-glass:           rgba(17, 24, 39, 0.7);
  --bg-glass-light:     rgba(99, 102, 241, 0.08);

  /* Typography */
  --font-main:          'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-numeric:       'Space Grotesk', monospace;

  /* Elevation & Shadows */
  --shadow-card:        0 4px 24px rgba(0, 0, 0, 0.4);
  --shadow-glow:        0 0 32px rgba(99, 102, 241, 0.15);
  --shadow-glow-accent: 0 0 24px rgba(6, 182, 212, 0.2);
}
```

### 2.2 Semantic Severity Tiers
- **Normal / Fluid (`LOW`):** `#10b981` (Emerald) — Occupancy $< 1.0\times$, clearance $\ge 0.22$, flow smooth.
- **Moderate Attention (`MEDIUM`):** `#f59e0b` (Amber) — Occupancy $1.0\times–1.2\times$, clearance $0.15–0.22$.
- **High Congestion (`HIGH`):** `#f97316` (Orange) — Occupancy $1.2\times–1.5\times$, clearance $0.10–0.15$.
- **Critical Bottleneck (`CRITICAL`):** `#ef4444` (Crimson) — Occupancy $\ge 1.5\times$, clearance $< 0.10$, persistent $\ge 4.0\text{s}$.

---

## 3. Component Architecture & UI Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│ App Header: StorePulse AI | FPS: 8.3 | Frame #1204 | STATUS: LIVE ●     │
├──────────────┬─────────────────────────────────────────────────────────┤
│ Sidebar      │ Main Viewport Content                                   │
│              │                                                         │
│ • Overview   │ ┌─────────────────────────────────────────────────────┐ │
│ • Live View  │ │ Top Alert / Disclaimer Banner                       │ │
│ • Zones      │ ├─────────────────────────────────────────────────────┤ │
│ • Flow       │ │ Primary Metric Summary Cards (2 to 4 Grid)          │ │
│ • Heatmaps   │ ├──────────────────────────────────┬──────────────────┤ │
│ • Queues     │ │ Interactive Canvas / Live Stream │ Property Panel   │ │
│ • Friction   │ │ SVG Floor Plan (800x500px)       │ Action Buttons   │ │
│ • Simulator  │ ├──────────────────────────────────┴──────────────────┤ │
│ • Scenarios  │ │ Detailed Breakdown Table / Heatmap Grid             │ │
│ • Settings   │ └─────────────────────────────────────────────────────┘ │
└──────────────┴─────────────────────────────────────────────────────────┘
```

---

## 4. Interactive Floor Plan Editor UX (`WhatIfSimulator.jsx`)

### 4.1 SVG Grid Engine
- **Canvas Resolution:** $800 \times 500\text{px}$ internal coordinate space, responsive SVG `viewBox`.
- **Magnetic Snapping:** All fixture translations and resize gestures snap to a uniform $40\text{px}$ Cartesian grid:
  $$\text{snap}(v) = \text{round}\left(\frac{v}{40}\right) \times 40$$
- **Element Types Supported:**
  - `shelf` (`#6366f1`): Standard grocery/department double-sided gondolas ($80\times160\text{px}$).
  - `checkout` (`#10b981`): Register lanes and POS counters ($120\times160\text{px}$).
  - `display` (`#8b5cf6`): Freestanding promotional endcaps ($60\times100\text{px}$).
  - `entrance` / `exit` (`#f59e0b` / `#06b6d4`): Turnstiles and store access points ($80\times80\text{px}$).
  - `obstacle` (`#ef4444`): Structural pillars and maintenance barriers.

### 4.2 Real-Time Collision & Overlap Visuals
- When any two physical fixtures collide (AABB intersection):
  - **Border Transformation:** Outlines transform to `#ef4444` with a dashed pattern (`strokeDasharray="4 2"`).
  - **Red Alert Dot:** Crimson badge renders at the upper-right corner of each colliding element.
  - **Global Alert Banner:** A prominent top banner displays:
    `ShieldAlert: Aisle Collision Warning: N overlapping pair(s) detected (e.g., Shelf B ↔ Shelf C).`
- **History & Recovery:** Dedicated `<Undo />` button backed by a 20-state snapshot stack and a single-click `<RotateCcw /> Reset to Baseline` action.

---

## 5. Transition Matrix Grid & Heatmap UX (`MovementFlow.jsx`)

### 5.1 Interactive Matrix Layout
- **Rows:** Origin zones ($i$).
- **Columns:** Destination zones ($j$).
- **Cells:** Render raw transition count alongside percentage probability:
  $$\text{Cell Value} = N_{ij} \quad (\% = P(j \mid i) \times 100)$$
- **Heatmap Color Intensity:** Background shading interpolates dynamically:
  $$\text{RGBA}\left(99, 102, 241, \min(0.70, 0.10 + 0.60 \cdot P(j \mid i))\right)$$
- **Outflow Totals:** Dedicated rightmost column displaying total outbound visitor journeys per department.
- **Data-Sufficiency Indicator Pill:**
  - Emerald Pill: `✓ Data Sufficient (N=22 events, Confidence: HIGH)`.
  - Amber Pill: `⚠ Insufficient Sample (N=2/5 events — Prior Weights Active)`.

---

## 6. Scenario Comparison Report UX (`ScenarioComparison.jsx`)

1. **Top Indicator Banner:** Declares whether simulation utilized live observed transitions or heuristic demand priors.
2. **Side-by-Side Summary Cards:** Compares Baseline vs. Proposed Space Utilization (%), Elements, Centroid Walking Distance (px), Route Conflict Score, and Bottleneck Risk Index (0–100).
3. **Zone Congestion Risk Cards Grid:** Displays zone name, clearance delta ($b_{\text{clear}}\% \to p_{\text{clear}}\%$) with direction badge, congestion tier badge (`LOW`/`MEDIUM`/`HIGH`/`CRITICAL`), and localized dwell impact text.
4. **Zero-Baseline Division Guards:** Metrics with baseline of 0 show `"0.0%"` or `"N/A (baseline is 0)"` without `NaN` or crashes.
