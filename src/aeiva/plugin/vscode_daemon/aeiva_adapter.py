from typing import Dict, Any

def generate_patch(task: Dict[str, Any]) -> Dict[str, Any]:
    sel_text = task.get("selectionText", "")
    start = task.get("offsetStart", 0)
    end = task.get("offsetEnd", 0)
    upper = sel_text.upper()
    return {
        "rationale": f"Stub patch for intent={task.get('intent')}",
        "edits": [
            {"op": "replace", "offsetStart": start, "offsetEnd": end, "text": upper}
        ],
        "guards": {"compileRisk": "unknown"},
        "telemetry": {"provider": "stub", "latencyMs": 5}
    }