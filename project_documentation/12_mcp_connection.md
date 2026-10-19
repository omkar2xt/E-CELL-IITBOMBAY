# StorePulse AI — Model Context Protocol (MCP) Connection Specification

**Document Version:** 1.0.0  
**Author:** Omkar Gurav  
**Target:** AI Assistants, Claude Desktop, Antigravity IDE, Enterprise Retail Copilots  
**Protocol Version:** MCP Spec 2024-11-05 / JSON-RPC 2.0  

---

## 1. Overview & Architecture

The **Model Context Protocol (MCP)** connection enables external Large Language Model (LLM) agents, developer environments, and automated retail copilot assistants to query, analyze, and control StorePulse AI in real time without writing ad-hoc scraper scripts or raw HTTP requests.

StorePulse AI exposes an **MCP Server** interface that bridges retail operations with AI reasoning engines. This gives conversational agents native access to:
1. Live retail telemetry (occupancy, dwell time, queue depths).
2. Spatial bottleneck alerts and flow friction indices.
3. Customer journey transition matrices.
4. Floor plan geometry validation.
5. What-if layout simulation experiments.

```
┌────────────────────────────────────────────────────────┐
│              Client (LLM / Copilot / IDE)              │
│        (e.g., Claude Desktop, Antigravity IDE)         │
└──────────────────────────┬─────────────────────────────┘
                           │ JSON-RPC 2.0 (stdio or SSE)
                           ▼
┌────────────────────────────────────────────────────────┐
│               StorePulse MCP Server Bridge              │
│          `backend/mcp_server.py` (FastMCP / AsyncIO)   │
└────────────┬─────────────────────────────┬─────────────┘
             │ In-Process / REST           │ In-Memory Query
             ▼                             ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│  FastAPI Analytics Engine │  │  ZoneAnalyticsEngine     │
│   (/api/zones, /layouts) │  │  (Real-Time Data State)   │
└──────────────────────────┘  └──────────────────────────┘
```

---

## 2. Supported MCP Capabilities

| Capability | Supported | Description |
|:---|:---:|:---|
| **Tools (`tools/list`, `tools/call`)** | **YES** | Exposes 5 callable functions to retrieve telemetry, validate layouts, and run simulations. |
| **Resources (`resources/list`, `resources/read`)** | **YES** | Exposes active layout snapshots, historical transition matrices, and store configurations as URI resources. |
| **Prompts (`prompts/list`, `prompts/get`)** | **YES** | Provides pre-engineered analytical prompts for retail floor optimization and bottleneck mitigation. |
| **Logging (`logging/setLevel`)** | **YES** | Streams real-time pipeline event warnings to connected LLM debugging consoles. |

---

## 3. Server Configuration & Setup

### 3.1 Antigravity / Claude Desktop Configuration

Add the StorePulse AI MCP server configuration to your MCP settings file:

- **Antigravity IDE:** `C:\Users\<USER>\.gemini\antigravity-ide\mcp_config.json`
- **Claude Desktop:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "storepulse-ai": {
      "command": "python",
      "args": [
        "-u",
        "e:\\ALL HACKTHONS\\E-cell-IIT-BOMBAY\\backend\\mcp_server.py"
      ],
      "env": {
        "STOREPULSE_API_URL": "http://127.0.0.1:8000",
        "STOREPULSE_DEBUG": "false",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

### 3.2 SSE Transport Configuration (Remote or Containerized)

When running StorePulse AI inside a Docker container or remote edge box:

```json
{
  "mcpServers": {
    "storepulse-ai-sse": {
      "url": "http://edge-node-01.storepulse.local:8000/mcp/sse",
      "transport": "sse"
    }
  }
}
```

---

## 4. MCP Tools Catalog

StorePulse AI registers five core tools through the MCP tool manifest:

### Tool 1: `get_store_metrics`
*Retrieves top-level store occupancy, queue lengths, average dwell time, and bottleneck counts.*

- **Parameters:**
  ```json
  {
    "type": "object",
    "properties": {
      "include_zones": {
        "type": "boolean",
        "description": "If true, includes breakdown per individual store zone."
      }
    }
  }
  ```
- **Return Signature:**
  ```json
  {
    "active_visitors": 14,
    "total_store_entries": 128,
    "active_bottlenecks": 1,
    "avg_store_dwell_seconds": 42.6,
    "zones": {
      "checkout_counter": {
        "current_occupancy": 4,
        "avg_dwell_seconds": 68.4,
        "is_bottleneck": true,
        "friction_score": 0.72
      }
    }
  }
  ```

---

### Tool 2: `get_zone_bottlenecks`
*Queries all active congestion hotspots where dwell time and density breach configured thresholds.*

- **Parameters:**
  ```json
  {
    "type": "object",
    "properties": {
      "severity_filter": {
        "type": "string",
        "enum": ["all", "warning", "critical"],
        "default": "all",
        "description": "Filter bottlenecks by severity level."
      }
    }
  }
  ```
- **Return Signature:**
  ```json
  {
    "timestamp": "2026-10-19T18:00:00Z",
    "bottlenecks": [
      {
        "zone_id": "checkout_counter",
        "zone_name": "Checkout Counter",
        "severity": "critical",
        "current_occupancy": 5,
        "max_capacity": 4,
        "avg_dwell_seconds": 74.2,
        "threshold_seconds": 45.0,
        "bottleneck_duration_seconds": 182.0,
        "root_cause": "Occupancy and dwell time both exceeded threshold for > 15 consecutive seconds."
      }
    ]
  }
  ```

---

### Tool 3: `get_transition_matrix`
*Returns the empirical Markov movement probability matrix across zones.*

- **Parameters:**
  ```json
  {
    "type": "object",
    "properties": {
      "min_observations": {
        "type": "integer",
        "default": 1,
        "description": "Minimum observed transitions required to report a path."
      }
    }
  }
  ```
- **Return Signature:**
  ```json
  {
    "total_transitions_recorded": 7,
    "data_sufficient": true,
    "evidence_type": "MEASURED_OBSERVED_EVENTS",
    "transitions": [
      {"from_zone": "entrance", "to_zone": "aisle_1", "count": 2, "probability": 1.0},
      {"from_zone": "aisle_1", "to_zone": "promo_display", "count": 1, "probability": 0.5},
      {"from_zone": "aisle_1", "to_zone": "checkout_counter", "count": 1, "probability": 0.5}
    ]
  }
  ```

---

### Tool 4: `validate_layout_geometry`
*Validates candidate store layout polygons against canvas boundaries, minimum clearance, and AABB overlaps.*

- **Parameters:**
  ```json
  {
    "type": "object",
    "required": ["canvas_width", "canvas_height", "zones"],
    "properties": {
      "canvas_width": {"type": "number"},
      "canvas_height": {"type": "number"},
      "zones": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["id", "name", "polygon"],
          "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "polygon": {
              "type": "array",
              "items": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 2,
                "maxItems": 2
              }
            }
          }
        }
      }
    }
  }
  ```
- **Return Signature:**
  ```json
  {
    "is_valid": true,
    "errors": [],
    "warnings": [
      "Zone 'promo_display' bounding box has only 4.2% clearance from 'aisle_1'."
    ],
    "zone_count": 4,
    "coverage_ratio": 0.38
  }
  ```

---

### Tool 5: `simulate_layout_scenario`
*Executes heuristic what-if simulation comparing a modified floor plan against baseline metrics.*

- **Parameters:**
  ```json
  {
    "type": "object",
    "required": ["candidate_layout_id"],
    "properties": {
      "candidate_layout_id": {"type": "string"},
      "modifier_percentage": {
        "type": "number",
        "default": 0.0,
        "description": "Simulated visitor footfall variance percentage (-50 to +100)."
      }
    }
  }
  ```
- **Return Signature:**
  ```json
  {
    "evidence_type": "HEURISTIC_ESTIMATE",
    "comparison": {
      "overall_friction_delta_pct": -14.2,
      "estimated_checkout_wait_delta_seconds": -18.5,
      "predicted_bottlenecks": [
        {
          "zone_id": "promo_display",
          "risk_score": 0.42,
          "verdict": "Low Risk (Decongested by layout shift)"
        }
      ]
    },
    "recommendation": "Adopt layout B: Widened primary corridor reduces predicted cashier queue spillage by ~18.5s."
  }
  ```

---

## 5. MCP Resources Catalog

External clients can subscribe to and read dynamic resources using `mcp.read_resource(uri)`:

| Resource URI | MIME Type | Description |
|:---|:---|:---|
| `storepulse://active_layout` | `application/json` | The currently live floor plan layout polygon coordinates and zone configurations. |
| `storepulse://transition_matrix` | `application/json` | Live cumulative transition counts and Markov transition probabilities. |
| `storepulse://bottleneck_alerts` | `application/json` | Real-time active bottleneck incidents and timestamps. |
| `storepulse://system_health` | `application/json` | Camera FPS, detection latency, tracking frame drops, and queue stats. |

---

## 6. MCP Prompts Catalog

The MCP server provides built-in prompt templates that LLMs can render to provide standardized executive advice:

### Prompt: `analyze_bottleneck_mitigation`
```markdown
You are the StorePulse AI Operations Consultant. Review the following live store data:
- Active Bottlenecks: {{bottlenecks}}
- Transition Matrix: {{transitions}}
- Current Zone Capacities: {{capacities}}

Deliver an action plan for the store manager covering:
1. Immediate tactical interventions (e.g., open backup register, clear aisle obstruction).
2. Root cause assessment based on customer inflow probability.
3. Long-term floor plan layout recommendations.
```

---

## 7. Implementation Code Reference (`backend/mcp_server.py`)

```python
"""
StorePulse AI — Model Context Protocol Server
Exposes live computer vision analytics & layout simulation to AI agents.
"""

import sys
import json
import asyncio
from typing import Any, Dict, List
import httpx

API_BASE = "http://127.0.0.1:8000"

async def call_api(endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=5.0) as client:
        if method == "GET":
            resp = await client.get(endpoint)
        else:
            resp = await client.post(endpoint, json=data)
        return resp.json()

# Tool Handler Dispatcher
async def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "get_store_metrics":
        return await call_api("/api/analytics/live")
    elif name == "get_zone_bottlenecks":
        return await call_api("/api/zones/bottlenecks")
    elif name == "get_transition_matrix":
        return await call_api("/api/zones/transitions")
    elif name == "validate_layout_geometry":
        return await call_api("/api/layouts/validate", method="POST", data=arguments)
    elif name == "simulate_layout_scenario":
        layout_id = arguments.get("candidate_layout_id", "layout_b")
        return await call_api(f"/api/layouts/{layout_id}/simulate")
    else:
        raise ValueError(f"Unknown tool: {name}")
```

---

## 8. Security & Privacy Guarantees

1. **Local-Only Stdio Transport:** By default, the MCP server runs via `stdio` subprocessing on `localhost`, preventing unauthorized external network traversal.
2. **Zero PII Leakage:** The MCP tools strictly return aggregate zone coordinates, counts, and dwell durations. No bounding box pixel crops, face images, or tracking coordinates are ever transmitted over MCP.
3. **Read-Only Analytics:** Tool execution cannot alter live camera feeds or tracking thresholds without explicit administrative credentials.
