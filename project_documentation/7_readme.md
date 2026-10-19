# StorePulse AI — Overview & Submission Summary

**Product:** StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator  
**Developer & Architect:** Omkar Gurav  
**Challenge:** Everseen Computer Vision AI Hackathon  
**Problem Statement 3:** Dwell-Time & Bottleneck Mapper  
**Submission Status:** Ready for Evaluation / Complete  
**License:** MIT  

---

## 1. Project Overview

**StorePulse AI** transforms standard retail camera feeds into high-value customer flow intelligence, explainable bottleneck alerts, and an interactive **What-If Floor Plan Layout Simulator**. 

Rather than treating computer vision as an isolated surveillance tool, StorePulse AI bridges the gap between **physical reality** and **strategic store planning**:
1. **Perception:** Real-time YOLO11n person detection and ByteTrack tracking continuously monitor store entrances, checkout queues, and departmental polygon zones.
2. **Intelligence:** Elapsed timestamp dwell-time engines, 2.0-second boundary hysteresis grace windows, and multi-signal bottleneck persistence algorithms identify congestion without false alarms.
3. **Simulation:** An interactive SVG floor-plan canvas allows managers to move shelves, shift promotional displays, and widen checkout aisles, immediately predicting changes in walking distance, aisle clearance, route conflicts, and bottleneck risk before remodeling.

---

## 2. Problem Statement 3 Alignment: Dwell-Time & Bottleneck Mapper

| Hackathon Requirement | StorePulse AI Implementation | Verification Status |
|---|---|---|
| **Zone-Based Dwell Tracking** | Timestamp-based elapsed calculation ($\Delta t = t_{\text{exit}} - t_{\text{enter}}$) with boundary hysteresis grace window. | **VERIFIED (14 Unit Tests)** |
| **Bottleneck Mapping & Alerting** | Multi-signal persistence window ($\ge 4.0\text{s}$), occupancy-to-capacity ratios, and actionable staff recommendations. | **VERIFIED** |
| **Flow Friction Scoring** | Standardized 0–100 composite index combining occupancy saturation, active dwell, and register queues. | **VERIFIED** |
| **Customer Journey Transitions** | Normalized routing matrix $P(j \mid i) = \frac{N_{ij}}{\sum_k N_{ik}}$ with unzoned hallway retention. | **VERIFIED** |
| **What-If Layout Simulation** | Interactive canvas editor with AABB fixture collision detection and before-and-after scenario comparisons. | **VERIFIED (8-Step E2E Workflow)** |
| **Responsible AI & Privacy** | Ephemeral integer tracking IDs only. Zero facial recognition, biometric storage, or raw video retention. | **VERIFIED** |

---

## 3. Key Technological Innovations

1. **Boundary Hysteresis Grace Window (2.0s):** Eliminates boundary jitter when customers linger on the edge of a department, preventing false duplicate entries.
2. **Elapsed Timestamp Precision:** Dwell times use real frame timestamps, preventing skew from camera framerate drops or CPU throttling.
3. **Connected Empirical Layout Simulator:** Connects live observed zone transition probabilities into customer demand weights for layout walkability calculations when $N \ge 5$.
4. **Real-Time Fixture Collision Warning (AABB):** Immediate red dashed visual warnings when virtual shelves overlap or obstruct customer corridors.
5. **Zero-Baseline Mathematical Safety:** Prevents division-by-zero crashes when baseline metrics are 0, safely rendering `"N/A (baseline is 0)"` while preserving directionality (`WORSE`/`BETTER`).

---

## 4. Verification & Testing Highlights

- **Automated Test Suite:** **46 automated tests passed in 12.72s (100% pass rate)** across API routes, CV tracking, zone analytics, Flow Friction, and layout simulation.
- **Frontend Production Build:** Clean Vite production build in 10.82s (0 errors).
- **Real CCTV Footprint:** Validated on `detection/vid/retail-cctv-footage.mp4` (640x480, 30 FPS, 300 frames) with YOLO11n + ByteTrack.
- **End-to-End Workflow:** Demonstrated all 8 workflow steps from opening baseline layout to collision validation, simulation, and scenario reload (transcript saved in `docs/workflow_execution_transcript.json`).

---

## 5. Quick Links & Documentation Index

- [Product Requirements Document (PRD)](1_PRD.md)
- [System & UI/UX Design](2_design.md)
- [System Architecture](3_architecture.md)
- [Data Storage & Schema Design](4_database.md)
- [REST & WebSocket API Reference](5_api.md)
- [AI & Subagent Specifications](6_agents.md)
- [Project Implementation Walkthrough](8_projectimplementation.md)
- [Setup & Initialization Guide](9_setup_and_initialisation.md)
- [Feature Development Breakdown](10_features_development.md)
- [Authentication & Security Policy](11_authentication_and_security.md)
- [Model Context Protocol (MCP) Connection](12_mcp_connection.md)
- [Hardware & Stream Integrations](13_integrations.md)
- [Testing & Quality Assurance Report](14_testing_and_qa.md)
- [Troubleshooting & Debugging Playbook](15_debugging.md)
