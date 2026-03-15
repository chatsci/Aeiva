# Dialogue Replay Report

- generated_at: `2026-02-13T15:10:13.448323+00:00`
- total_scenarios: `2`
- passed_scenarios: `0`
- failed_scenarios: `2`
- success_rate: `0.0000`
- total_turns: `2`
- timed_out_turns: `2`
- avg_latency_seconds: `25.00`

## Scenario Results

| scenario_id | passed | turns | errors |
|---|---:|---:|---:|
| metaui_dialogue_ui_create | 0 | 1 | 3 |
| metaui_form_submit_flow | 0 | 1 | 3 |

## Errors

- [metaui_dialogue_ui_create] metaui_dialogue_ui_create/turn[0] latency 25.01s > 20.00s
- [metaui_dialogue_ui_create] metaui_dialogue_ui_create/turn[0] MetaUI session_count 0 < required 1
- [metaui_dialogue_ui_create] metaui_dialogue_ui_create/turn[0] all MetaUI sessions have empty components.
- [metaui_form_submit_flow] metaui_form_submit_flow/turn[0] latency 25.00s > 20.00s
- [metaui_form_submit_flow] metaui_form_submit_flow/turn[0] MetaUI session_count 0 < required 1
- [metaui_form_submit_flow] metaui_form_submit_flow/turn[0] all MetaUI sessions have empty components.
