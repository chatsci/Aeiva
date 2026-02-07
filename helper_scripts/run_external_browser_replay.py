#!/usr/bin/env python3
"""Run external browser replay benchmark and write JSON/Markdown reports."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from aeiva.tool.meta.browser_stack.external_replay import (
    build_external_replay_catalog,
    render_external_replay_markdown,
    run_external_replay,
    select_external_replay_scenarios,
)
from aeiva.tool.meta.browser_stack.security import BrowserSecurityPolicy
from aeiva.tool.meta.browser_stack.service import BrowserService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run external browser replay scenarios.")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode.")
    parser.add_argument("--timeout-ms", type=int, default=30_000, help="Per-step timeout in milliseconds.")
    parser.add_argument("--limit", type=int, default=40, help="Scenario count limit.")
    parser.add_argument(
        "--category",
        action="append",
        default=[],
        help="Filter category (repeatable), e.g. --category travel_flights",
    )
    parser.add_argument(
        "--output-dir",
        default="docs/reports",
        help="Directory for benchmark reports.",
    )
    parser.add_argument(
        "--profile-prefix",
        default="external-replay",
        help="Profile prefix used by BrowserService sessions.",
    )
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> int:
    catalog = build_external_replay_catalog()
    selected = select_external_replay_scenarios(
        scenarios=catalog,
        categories=args.category,
        limit=args.limit,
    )
    if not selected:
        print("No scenarios selected. Adjust --category/--limit.")
        return 2

    service = BrowserService(
        security_policy=BrowserSecurityPolicy(
            allow_evaluate=False,
            allow_private_network_requests=False,
            request_allowlist=(),
            allow_any_upload_path=False,
            upload_roots=(),
        )
    )
    report = await run_external_replay(
        service=service,
        scenarios=selected,
        profile_prefix=args.profile_prefix,
        headless=bool(args.headless),
        timeout_ms=int(args.timeout_ms),
    )

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    json_path = output_dir / f"external-browser-replay-{stamp}.json"
    md_path = output_dir / f"external-browser-replay-{stamp}.md"
    json_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_external_replay_markdown(report), encoding="utf-8")

    print(f"Scenarios: {report.total_scenarios}")
    print(f"Passed: {report.passed_scenarios}")
    print(f"Failed: {report.failed_scenarios}")
    print(f"Success rate: {report.success_rate:.4f}")
    print(f"P95 duration (ms): {report.p95_scenario_duration_ms:.2f}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    return 0 if report.failed_scenarios == 0 else 1


def main() -> int:
    args = _parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
