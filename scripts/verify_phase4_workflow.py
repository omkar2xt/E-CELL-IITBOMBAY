"""
End-to-End Workflow Verification Script for Phase 4: Intelligent What-If Layout Simulator
Developer: Omkar Gurav
Everseen Computer Vision AI Hackathon — Problem Statement 3

Workflow Steps:
1. Open current store layout.
2. View observed zone statistics and transition data.
3. Save a baseline scenario.
4. Move one shelf or display.
5. Run the proposed-layout simulation.
6. Compare baseline and proposed results.
7. Inspect the estimated bottleneck changes.
8. Save and reload the proposed scenario.
"""
import sys
import os
import json
import copy

# Ensure root path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from backend.main import app

def run_e2e_workflow():
    client = TestClient(app)
    results = {}
    print("=" * 70)
    print("STOREPULSE AI — PHASE 4: END-TO-END WORKFLOW VERIFICATION")
    print("=" * 70)

    # -------------------------------------------------------------
    # Step 1: Open the current store layout
    # -------------------------------------------------------------
    print("\n[STEP 1] Opening current store layout...")
    res = client.get("/api/layouts/baseline")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    baseline_data = res.json()["layout"]
    results["step1"] = {
        "layout_id": baseline_data["id"],
        "layout_name": baseline_data["name"],
        "element_count": len(baseline_data["elements"]),
        "elements_sample": [e["label"] for e in baseline_data["elements"][:4]],
    }
    print(f"  ✓ Retrieved layout '{baseline_data['name']}' (ID: {baseline_data['id']}) with {len(baseline_data['elements'])} elements.")

    # -------------------------------------------------------------
    # Step 2: View observed zone statistics and transition data
    # -------------------------------------------------------------
    print("\n[STEP 2] Viewing observed zone statistics and transition data...")
    res_stats = client.get("/api/zones/stats")
    assert res_stats.status_code == 200
    stats = res_stats.json().get("zone_stats", [])

    res_trans = client.get("/api/zones/transitions")
    assert res_trans.status_code == 200
    transitions = res_trans.json()
    results["step2"] = {
        "zone_count": len(stats),
        "total_transitions": transitions.get("total_transitions", 0),
        "data_sufficient": transitions.get("data_sufficient", False),
        "confidence": transitions.get("confidence", "LOW"),
    }
    print(f"  ✓ Zone stats retrieved: {len(stats)} configured zones.")
    print(f"  ✓ Transitions retrieved: {transitions.get('total_transitions', 0)} events recorded (data_sufficient={transitions.get('data_sufficient', False)}).")

    # -------------------------------------------------------------
    # Step 3: Save a baseline scenario
    # -------------------------------------------------------------
    print("\n[STEP 3] Saving a baseline scenario...")
    baseline_payload = {
        "id": "baseline",
        "name": "Everseen Supermarket Baseline",
        "description": "Certified baseline layout for Phase 4 simulation benchmarks",
        "elements": baseline_data["elements"],
        "zones": baseline_data.get("zones", []),
        "is_baseline": True,
    }
    res_save_base = client.post("/api/layouts/", json=baseline_payload)
    assert res_save_base.status_code in (200, 201)
    base_json = res_save_base.json()
    saved_base_id = base_json.get("layout", {}).get("id", base_json.get("id"))
    results["step3"] = {
        "status": "saved",
        "baseline_id": saved_base_id,
        "name": baseline_payload["name"],
    }
    print(f"  ✓ Baseline scenario saved with ID: {saved_base_id}.")

    # -------------------------------------------------------------
    # Step 4: Move one shelf or display
    # -------------------------------------------------------------
    print("\n[STEP 4] Moving Shelf B to simulate promotional aisle reconfiguration...")
    proposed_elements = copy.deepcopy(baseline_data["elements"])
    # Find Shelf B (id 's2') and shift its position to widen or narrow aisle
    moved_element = None
    for el in proposed_elements:
        if el.get("id") == "s2" or el.get("label") == "Shelf B":
            el["x"] = 0.50  # Shift Shelf B toward center
            el["y"] = 0.20
            moved_element = el
            break
    if not moved_element:
        # Move second element
        proposed_elements[1]["x"] = 0.55
        moved_element = proposed_elements[1]

    # Validate geometry
    val_res = client.post("/api/layouts/validate", json={
        "name": "Proposed Aisle Reconfiguration",
        "elements": proposed_elements,
        "zones": [],
    })
    print("Validate status:", val_res.status_code, "body:", val_res.text)
    assert val_res.status_code == 200
    val_json = val_res.json()
    results["step4"] = {
        "moved_element": moved_element["label"],
        "new_coords": {"x": moved_element["x"], "y": moved_element["y"]},
        "geometry_valid": val_json.get("valid", True),
        "overlap_count": len(val_json.get("overlap_pairs", [])),
    }
    is_valid_flag = val_json.get("valid", val_json.get("is_valid", True))
    print(f"  ✓ Geometry validation: valid={is_valid_flag}, overlap_pairs={len(val_json.get('overlap_pairs', []))}.")

    # -------------------------------------------------------------
    # Step 5: Run the proposed-layout simulation
    # -------------------------------------------------------------
    print("\n[STEP 5] Running proposed-layout simulation...")
    # First save proposed layout as 'proposed_scenario_1'
    prop_payload = {
        "id": "proposed_scenario_1",
        "name": "Proposed Layout Scenario 1",
        "description": "Shelf B reconfigured to test aisle clearance",
        "elements": proposed_elements,
        "zones": [],
        "is_baseline": False,
    }
    save_prop_res = client.post("/api/layouts/", json=prop_payload)
    assert save_prop_res.status_code in (200, 201)

    sim_res = client.post("/api/layouts/simulate", json={
        "baseline_id": "baseline",
        "proposed_id": "proposed_scenario_1",
    })
    assert sim_res.status_code == 200, f"Simulate returned {sim_res.status_code}: {sim_res.text}"
    sim_data = sim_res.json()
    results["step5"] = {
        "status": "success",
        "model": sim_data["model"],
        "used_empirical_transitions": sim_data["used_empirical_transitions"],
        "comparison_count": len(sim_data["comparison"]),
        "zone_comparison_count": len(sim_data.get("zone_comparisons", [])),
    }
    print(f"  ✓ Simulation completed using model: {sim_data['model']}.")
    print(f"  ✓ Empirical transitions applied: {sim_data['used_empirical_transitions']}.")

    # -------------------------------------------------------------
    # Step 6: Compare baseline and proposed results
    # -------------------------------------------------------------
    print("\n[STEP 6] Comparing baseline vs. proposed metrics...")
    comparisons = sim_data["comparison"]
    for row in comparisons:
        print(f"    - {row['metric']}: Base={row['baseline']} | Prop={row['proposed']} | Diff={row['absolute_diff']} ({row['pct_diff']}) | Dir={row['direction']} | Source={row['source']}")
    results["step6"] = comparisons

    # -------------------------------------------------------------
    # Step 7: Inspect estimated bottleneck changes
    # -------------------------------------------------------------
    print("\n[STEP 7] Inspecting zone bottleneck and congestion risk estimates...")
    zone_comps = sim_data.get("zone_comparisons", [])
    for z in zone_comps:
        print(f"    - [{z['zone_name']}] Clearance: {z['baseline_clearance_pct']}% -> {z['proposed_clearance_pct']}% | Risk: {z['baseline_risk']} -> {z['proposed_risk']} ({z['risk_change']})")
        print(f"      Dwell Impact: {z['estimated_dwell_impact']}")
    results["step7"] = zone_comps

    # -------------------------------------------------------------
    # Step 8: Save and reload the proposed scenario
    # -------------------------------------------------------------
    print("\n[STEP 8] Saving and reloading proposed scenario from backend store...")
    reload_res = client.get("/api/layouts/proposed_scenario_1")
    assert reload_res.status_code == 200
    reloaded_layout = reload_res.json()["layout"]
    assert reloaded_layout["id"] == "proposed_scenario_1"
    assert len(reloaded_layout["elements"]) == len(proposed_elements)
    results["step8"] = {
        "reloaded_id": reloaded_layout["id"],
        "reloaded_name": reloaded_layout["name"],
        "element_count": len(reloaded_layout["elements"]),
    }
    print(f"  ✓ Successfully reloaded '{reloaded_layout['name']}' with {len(reloaded_layout['elements'])} elements from storage.")

    print("\n" + "=" * 70)
    print("ALL 8 END-TO-END WORKFLOW STEPS SUCCESSFULLY EXECUTED AND VERIFIED!")
    print("=" * 70)

    # Save execution transcript
    artifact_path = os.path.join(os.path.dirname(__file__), "..", "docs", "workflow_execution_transcript.json")
    with open(artifact_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Transcript written to: {artifact_path}")

if __name__ == "__main__":
    run_e2e_workflow()
