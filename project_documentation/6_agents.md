# StorePulse AI — AI & Subagent Specifications / Decision Logic

**Document:** AI & Subagent Specifications  
**Author:** Omkar Gurav  
**Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator  
**Version:** 1.0.0  

---

## 1. Agentic Architecture Overview

StorePulse AI incorporates dedicated autonomous decision-making agents across its perception, analytical, and operational layers. Rather than operating as static rule-based scripts, each agent encapsulates domain-specific heuristics, temporal state machines, and explainability generators:

```
┌────────────────────────────────────────────────────────────┐
│ StorePulse AI Agent Mesh                                  │
├──────────────────────────────┬─────────────────────────────┤
│ 1. Perception Agent          │ 2. Bottleneck Agent         │
│ • Bounding Box Association   │ • Multi-Signal Congestion   │
│ • Occlusion & Track Buffer   │ • Boundary Hysteresis       │
│ • Dead-Zone Line Crossing    │ • Evidence & Staff Advice   │
├──────────────────────────────┼─────────────────────────────┤
│ 3. Layout Simulator Agent    │ 4. Executive MCP Assistant  │
│ • Aisle Clearance Modeling   │ • Tool-Use (Model Context)  │
│ • Empirical Routing Prior    │ • Autonomous Layout Audits  │
│ • Collision Resolution       │ • Natural Language Reports  │
└──────────────────────────────┴─────────────────────────────┘
```

---

## 2. Agent Catalog & State Machine Specifications

### 2.1 Perception & Tracking Agent (`ByteTrackPersonTracker`)
- **Primary Mission:** Maintain persistent numeric identities ($ID_k$) of customers moving across variable lighting, retail occlusions (shelves, pillars), and high-density interactions.
- **Decision Logic:**
  1. **Primary Hungarian Matching:** Associates high-confidence YOLO detections ($\text{conf} \ge 0.40$) with existing Kalman state predictions.
  2. **Secondary Hungarian Matching:** Attempts recovery of low-confidence detections against unconfirmed tracks before declaring a track lost.
  3. **Occlusion Buffer:** Retains track identity in volatile memory for $30\text{ frames}$ (~1.0s) of camera occlusion before discarding.
  4. **Privacy Enforcer:** Prevents facial detection or demographic identity storage; strips biometrics at the perception boundary.

---

### 2.2 Zone Analytics & Bottleneck Alert Agent (`ZoneAnalyticsEngine`)
- **Primary Mission:** Monitor spatial dwell times, evaluate multi-factor localized congestion, and escalate actionable operational staff recommendations.
- **State Machine Rules:**
  - **Boundary Jitter Suppression:** When a visitor crosses a zone polygon edge, enters a 2.0s pending exit buffer. If the person steps back into the zone within 2.0s, the exit is canceled—eliminating boundary jitter and false entry inflation.
  - **Track Interruption Watchdog:** If a person disappears inside a zone for $> 5.0\text{s}$ (e.g. obscured behind a tall display), the visit is finalized with `interrupted = True` at the last seen coordinate.
  - **Bottleneck Severity Escalation:**
    $$\text{Severity} = \begin{cases}
    \text{CRITICAL} & \text{if } \text{Occupancy} \ge 1.5 \times \text{Capacity} \land t_{\text{sustained}} \ge 4.0\text{s} \\
    \text{HIGH} & \text{if } \text{Occupancy} \ge 1.2 \times \text{Capacity} \land t_{\text{sustained}} \ge 4.0\text{s} \\
    \text{MEDIUM} & \text{if } \text{Occupancy} \ge 1.0 \times \text{Capacity} \lor \text{Linger} > \text{Threshold} \\
    \text{LOW} & \text{otherwise}
    \end{cases}$$
  - **Actionable Explainability:** Generates human-readable evidence arrays and contextual advice:
    `"Deploy additional cashier to Checkout Counter (8.5s sustained load)."`

---

### 2.3 Heuristic Layout Simulation Agent (`LayoutSimulator`)
- **Primary Mission:** Evaluate proposed spatial reconfigurations against empirical baseline movement demand, estimating walking distance, route conflict, and localized aisle bottlenecks.
- **Decision Logic:**
  1. **Geometry Audit:** Scans all fixtures using 2D Axis-Aligned Bounding Box (AABB) intersection tests. Identifies overlapping fixture pairs that obstruct aisles.
  2. **Aisle Clearance Extraction:** Evaluates Euclidean distance from zone centroids to the nearest fixture boundary ($d_{\text{clearance}}$).
  3. **Empirical Prior Weighting:**
     - If $N_{\text{observed}} \ge 5$: Weights route walking distances according to empirical transition probabilities $P(j \mid i)$.
     - If $N_{\text{observed}} < 5$: Activates documented category demand weights with explicit fallback disclaimers.
  4. **Zero-Baseline Division Guard:** Handles zero-baseline conflict scores safely, outputting `"N/A (baseline is 0)"` while accurately labeling direction (`WORSE`/`BETTER`).

---

### 2.4 Model Context Protocol (MCP) Executive Agent
- **Primary Mission:** Expose StorePulse AI spatial telemetry and layout simulation capabilities to external autonomous agents and Large Language Models (LLMs) via standard MCP protocols.
- **Exposed MCP Tools:**
  - `get_store_metrics()`: Queries live occupancy, queue counts, and Flow Friction.
  - `get_zone_bottlenecks()`: Inspects active bottleneck severity, evidence, and recommendations.
  - `get_transition_matrix()`: Queries conditional zone transition routing probabilities.
  - `validate_layout_geometry(elements)`: Evaluates physical layout fixtures for AABB overlaps.
  - `simulate_layout_scenario(baseline_id, proposed_id)`: Generates full before-and-after comparison metrics.
- **Autonomous Workflow:** Enables an LLM agent to audit a store layout, detect a bottleneck at Checkout, simulate widening the checkout aisle by moving Shelf B, and return an executive ROI summary to the retail director.
