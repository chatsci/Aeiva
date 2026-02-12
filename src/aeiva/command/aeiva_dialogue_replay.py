"""
Run multi-turn dialogue replay scenarios against a real AEIVA runtime.

Example:
    uv run aeiva-dialogue-replay \
      -c configs/agent_config.yaml \
      -s docs/examples/dialogue_replay/metaui_dialogue_suite.yaml
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional, Sequence

import click

from aeiva.command.command_utils import (
    get_package_root,
    prepare_runtime_config,
    setup_command_logger,
)
from aeiva.testing.dialogue_replay import (
    GatewayDialogueReplay,
    build_dialogue_report,
    load_dialogue_scenarios_from_file,
    render_dialogue_report_markdown,
    select_scenarios,
)
from aeiva.util.file_utils import from_json_or_yaml


PACKAGE_ROOT = get_package_root()
_json_config = PACKAGE_ROOT / "configs" / "agent_config.json"
_yaml_config = PACKAGE_ROOT / "configs" / "agent_config.yaml"
DEFAULT_CONFIG_PATH = _json_config if _json_config.exists() else _yaml_config


async def _run_dialogue_replay_async(
    *,
    config_dict: dict,
    scenarios,
    route_token: str,
    fail_fast: bool,
) -> tuple:
    runner = await GatewayDialogueReplay.from_config(
        config_dict=config_dict,
        route_token=route_token,
    )
    results = []
    try:
        for scenario in scenarios:
            scenario_result = await runner.run_scenario(
                scenario,
                fail_fast=fail_fast,
            )
            results.append(scenario_result)
    finally:
        await runner.stop()
    return tuple(results)


def _write_text_if_needed(path: Optional[str], content: str) -> None:
    if not path:
        return
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


@click.command(name="aeiva-dialogue-replay")
@click.option(
    "--config",
    "-c",
    default=str(DEFAULT_CONFIG_PATH),
    help="Path to AEIVA runtime config (JSON/YAML).",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--scenarios",
    "-s",
    required=True,
    help="Path to dialogue replay scenario file (JSON/YAML).",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--scenario-id",
    "scenario_ids",
    multiple=True,
    help="Run only selected scenario id(s). Can be repeated.",
)
@click.option(
    "--route-token",
    default="gradio",
    show_default=True,
    help="Route token used by ResponseQueueGateway.",
)
@click.option(
    "--fail-fast",
    is_flag=True,
    help="Stop each scenario at first failing turn expectation.",
)
@click.option(
    "--output-json",
    default=None,
    type=click.Path(dir_okay=False),
    help="Optional JSON report output path.",
)
@click.option(
    "--output-md",
    default=None,
    type=click.Path(dir_okay=False),
    help="Optional Markdown report output path.",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging.")
def run(
    config: str,
    scenarios: str,
    scenario_ids: Sequence[str],
    route_token: str,
    fail_fast: bool,
    output_json: Optional[str],
    output_md: Optional[str],
    verbose: bool,
) -> None:
    logger = setup_command_logger(
        log_filename="aeiva-dialogue-replay.log",
        verbose=verbose,
    )
    click.echo(f"Loading configuration from {config}")
    click.echo(f"Loading replay scenarios from {scenarios}")

    try:
        config_payload = from_json_or_yaml(Path(config))
        prepare_runtime_config(config_payload)
        all_scenarios = load_dialogue_scenarios_from_file(scenarios)
        selected_scenarios = select_scenarios(
            all_scenarios,
            scenario_ids=scenario_ids,
        )
    except Exception as exc:
        logger.error("Failed to prepare replay inputs: %s", exc)
        click.echo(f"Error: {exc}")
        raise SystemExit(1)

    if not selected_scenarios:
        click.echo("Error: no scenarios selected.")
        raise SystemExit(1)

    try:
        results = asyncio.run(
            _run_dialogue_replay_async(
                config_dict=config_payload,
                scenarios=selected_scenarios,
                route_token=route_token,
                fail_fast=fail_fast,
            )
        )
    except KeyboardInterrupt:
        click.echo("Interrupted.")
        raise SystemExit(130)
    except Exception as exc:
        logger.error("Replay run failed: %s", exc)
        click.echo(f"Error: {exc}")
        raise SystemExit(1)

    report = build_dialogue_report(results)
    report_json_text = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
    report_markdown = render_dialogue_report_markdown(report)
    _write_text_if_needed(output_json, report_json_text + "\n")
    _write_text_if_needed(output_md, report_markdown)

    click.echo(f"total_scenarios: {report.total_scenarios}")
    click.echo(f"passed_scenarios: {report.passed_scenarios}")
    click.echo(f"failed_scenarios: {report.failed_scenarios}")
    click.echo(f"total_turns: {report.total_turns}")
    click.echo(f"timed_out_turns: {report.timed_out_turns}")
    click.echo(f"avg_latency_seconds: {report.avg_latency_seconds:.2f}")

    if report.failed_scenarios > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    run()
