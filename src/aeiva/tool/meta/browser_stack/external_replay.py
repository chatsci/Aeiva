"""External website replay scenarios and benchmark runner for BrowserService."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class ExternalReplayStep:
    operation: str
    url: Optional[str] = None
    selector: Optional[str] = None
    text: Optional[str] = None
    query: Optional[str] = None
    request: Optional[Dict[str, Any]] = None
    target_id: Optional[str] = None
    ref: Optional[str] = None
    timeout_ms: Optional[int] = None
    expect_contains: Optional[str | Sequence[str]] = None


@dataclass(frozen=True)
class ExternalReplayScenario:
    scenario_id: str
    category: str
    title: str
    steps: List[ExternalReplayStep]
    tags: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ExternalReplayFailure:
    scenario_id: str
    step_index: int
    operation: str
    reason: str
    details: Optional[str] = None


@dataclass(frozen=True)
class ExternalReplayScenarioResult:
    scenario_id: str
    category: str
    title: str
    success: bool
    step_count: int
    completed_steps: int
    duration_ms: float
    retries: int
    failure: Optional[ExternalReplayFailure] = None


@dataclass
class ExternalReplayReport:
    generated_at: str
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    total_steps: int
    completed_steps: int
    total_retries: int
    scenario_results: List[ExternalReplayScenarioResult] = field(default_factory=list)
    failures: List[ExternalReplayFailure] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_scenarios <= 0:
            return 0.0
        return self.passed_scenarios / float(self.total_scenarios)

    @property
    def p95_scenario_duration_ms(self) -> float:
        if not self.scenario_results:
            return 0.0
        values = sorted(item.duration_ms for item in self.scenario_results)
        index = max(0, int((len(values) * 0.95) - 1))
        return float(values[min(index, len(values) - 1)])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_scenarios": self.total_scenarios,
            "passed_scenarios": self.passed_scenarios,
            "failed_scenarios": self.failed_scenarios,
            "success_rate": self.success_rate,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "total_retries": self.total_retries,
            "p95_scenario_duration_ms": self.p95_scenario_duration_ms,
            "scenario_results": [
                {
                    "scenario_id": item.scenario_id,
                    "category": item.category,
                    "title": item.title,
                    "success": item.success,
                    "step_count": item.step_count,
                    "completed_steps": item.completed_steps,
                    "duration_ms": item.duration_ms,
                    "retries": item.retries,
                    "failure": (
                        {
                            "scenario_id": item.failure.scenario_id,
                            "step_index": item.failure.step_index,
                            "operation": item.failure.operation,
                            "reason": item.failure.reason,
                            "details": item.failure.details,
                        }
                        if item.failure
                        else None
                    ),
                }
                for item in self.scenario_results
            ],
            "failures": [
                {
                    "scenario_id": item.scenario_id,
                    "step_index": item.step_index,
                    "operation": item.operation,
                    "reason": item.reason,
                    "details": item.details,
                }
                for item in self.failures
            ],
        }


def _extract_search_host(url: str) -> str:
    if "://" not in url:
        return url
    return url.split("://", 1)[-1].split("/", 1)[0]


def _mk_catalog(
    *,
    category: str,
    base_urls: Sequence[str],
    queries: Sequence[str],
    tag: str,
) -> List[ExternalReplayScenario]:
    scenarios: List[ExternalReplayScenario] = []
    for idx, query in enumerate(queries):
        base_url = base_urls[idx % len(base_urls)]
        scenario_id = f"{category}-{idx + 1:02d}"
        query_param = query.replace(" ", "+")
        if "?" in base_url:
            nav_url = f"{base_url}&q={query_param}"
        elif base_url.rstrip("/").endswith("search"):
            nav_url = f"{base_url}?q={query_param}"
        else:
            nav_url = base_url
        steps = [
            ExternalReplayStep(operation="navigate", url=nav_url),
            ExternalReplayStep(operation="wait", request={"load_state": "domcontentloaded"}),
            ExternalReplayStep(operation="snapshot", request={"limit": 120}),
        ]
        scenarios.append(
            ExternalReplayScenario(
                scenario_id=scenario_id,
                category=category,
                title=f"{category.replace('_', ' ').title()} replay for '{query}'",
                steps=steps,
                tags=(tag, _extract_search_host(base_url)),
            )
        )
    return scenarios


def build_external_replay_catalog() -> List[ExternalReplayScenario]:
    scenarios: List[ExternalReplayScenario] = []
    scenarios.extend(
        _mk_catalog(
            category="search",
            base_urls=(
                "https://www.google.com/search",
                "https://www.bing.com/search",
                "https://duckduckgo.com",
            ),
            queries=(
                "montreal weather tomorrow",
                "python asyncio tutorial",
                "best productivity tips",
                "gpu benchmark latest",
                "travel checklist",
                "local music festival",
                "ai browser automation",
                "sqlite optimization guide",
                "what is kuzu graph db",
                "playwright docs",
                "chroma db tutorial",
                "flight baggage allowance",
            ),
            tag="general",
        )
    )
    scenarios.extend(
        _mk_catalog(
            category="travel_flights",
            base_urls=(
                "https://www.google.com/travel/flights",
                "https://www.kayak.com/flights",
                "https://www.skyscanner.com/transport/flights",
                "https://www.trip.com/flights",
            ),
            queries=(
                "YUL PVG 2026-02-09 one way",
                "YUL PEK cheapest",
                "montreal to shanghai business class",
                "toronto to tokyo direct",
                "vancouver to paris one way",
                "montreal to london economy",
                "montreal to beijing max 1 stop",
                "new york to shanghai",
                "san francisco to seoul",
                "chicago to hong kong",
                "boston to singapore",
                "calgary to amsterdam",
                "edmonton to dubai",
                "ottawa to berlin",
            ),
            tag="travel",
        )
    )
    scenarios.extend(
        _mk_catalog(
            category="travel_hotels",
            base_urls=(
                "https://www.booking.com/searchresults.html",
                "https://www.expedia.com/Hotel-Search",
                "https://www.hotels.com/Hotel-Search",
            ),
            queries=(
                "Montreal 2026-02-09 2 nights",
                "Shanghai 2026-02-10 3 nights",
                "Tokyo downtown 2 guests",
                "Paris near center",
                "Beijing daxing area",
                "New York times square",
                "Vancouver downtown",
                "Toronto union station",
                "Barcelona beach hotel",
                "Berlin central station",
                "Amsterdam canals",
                "Seoul gangnam",
            ),
            tag="travel",
        )
    )
    scenarios.extend(
        _mk_catalog(
            category="media",
            base_urls=(
                "https://www.youtube.com/results",
                "https://soundcloud.com/search",
                "https://vimeo.com/search",
            ),
            queries=(
                "interesting science documentary",
                "jazz piano live",
                "coding music focus",
                "travel vlog japan",
                "language learning playlist",
                "llm tools demo",
                "python tutorial video",
                "database design lecture",
                "best guitar solo",
                "productivity talk",
            ),
            tag="media",
        )
    )
    scenarios.extend(
        _mk_catalog(
            category="docs",
            base_urls=(
                "https://github.com/search",
                "https://stackoverflow.com/search",
                "https://developer.mozilla.org/en-US/search",
                "https://docs.python.org/3/search.html",
            ),
            queries=(
                "playwright python click",
                "asyncio queue timeout",
                "css selector aria-label",
                "sqlite pragma journal mode",
                "chromadb python client",
                "kuzu database query",
                "python dataclass frozen",
                "pytest async fixtures",
                "websocket reconnect strategy",
                "rate limiting middleware",
            ),
            tag="knowledge",
        )
    )
    scenarios.extend(
        _mk_catalog(
            category="shopping",
            base_urls=(
                "https://www.amazon.com/s",
                "https://www.ebay.com/sch/i.html",
                "https://www.bestbuy.com/site/searchpage.jsp",
                "https://www.walmart.com/search",
            ),
            queries=(
                "noise cancelling headphones",
                "mechanical keyboard",
                "portable ssd 1tb",
                "travel backpack carry on",
                "webcam 4k",
                "usb-c hub",
                "bluetooth speaker",
                "ergonomic chair",
                "gaming mouse",
                "monitor arm",
            ),
            tag="commerce",
        )
    )
    scenarios.extend(
        _mk_catalog(
            category="maps",
            base_urls=(
                "https://www.google.com/maps/search",
                "https://www.bing.com/maps",
                "https://www.openstreetmap.org/search",
            ),
            queries=(
                "Montreal airport",
                "Shanghai Pudong airport",
                "nearest train station",
                "hotel near downtown",
                "coffee shop nearby",
                "museum around me",
            ),
            tag="geo",
        )
    )
    scenarios.extend(
        _mk_catalog(
            category="productivity",
            base_urls=(
                "https://calendar.google.com",
                "https://mail.google.com",
                "https://notion.so",
                "https://trello.com",
                "https://docs.google.com",
                "https://drive.google.com",
                "https://app.asana.com",
                "https://slack.com/signin",
            ),
            queries=(
                "daily planning",
                "team standup notes",
                "project milestone board",
                "weekly review checklist",
                "meeting agenda template",
                "todo prioritization matrix",
                "release notes draft",
                "research notes workspace",
            ),
            tag="workflow",
        )
    )
    return scenarios


def select_external_replay_scenarios(
    *,
    scenarios: Sequence[ExternalReplayScenario],
    categories: Optional[Sequence[str]] = None,
    limit: Optional[int] = None,
) -> List[ExternalReplayScenario]:
    category_filter = {str(item).strip().casefold() for item in (categories or []) if str(item).strip()}
    filtered: List[ExternalReplayScenario] = []
    for item in scenarios:
        if category_filter and item.category.casefold() not in category_filter:
            continue
        filtered.append(item)
        if limit is not None and len(filtered) >= max(0, int(limit)):
            break
    return filtered


def _normalize_expectation(value: Optional[str | Sequence[str]]) -> Tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        clean = value.strip()
        return (clean,) if clean else ()
    out: List[str] = []
    for item in value:
        clean = str(item).strip()
        if clean:
            out.append(clean)
    return tuple(out)


def _collect_payload_text(payload: Dict[str, Any]) -> str:
    candidates = [
        payload.get("text"),
        payload.get("snapshot"),
        payload.get("html"),
        payload.get("url"),
        payload.get("title"),
        payload.get("error"),
    ]
    return "\n".join(str(item) for item in candidates if item is not None)


async def run_external_replay(
    *,
    service: Any,
    scenarios: Sequence[ExternalReplayScenario],
    profile_prefix: str = "external-replay",
    headless: bool = False,
    timeout_ms: int = 30_000,
) -> ExternalReplayReport:
    report = ExternalReplayReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_scenarios=len(scenarios),
        passed_scenarios=0,
        failed_scenarios=0,
        total_steps=0,
        completed_steps=0,
        total_retries=0,
    )

    for index, scenario in enumerate(scenarios, start=1):
        profile = f"{profile_prefix}-{index:03d}"
        started = time.perf_counter()
        failure: Optional[ExternalReplayFailure] = None
        completed_steps = 0
        retries = 0
        for step_index, step in enumerate(scenario.steps):
            report.total_steps += 1
            step_timeout = int(step.timeout_ms) if step.timeout_ms is not None else int(timeout_ms)
            try:
                payload = await service.execute(
                    operation=step.operation,
                    profile=profile,
                    headless=headless,
                    timeout=step_timeout,
                    url=step.url,
                    selector=step.selector,
                    text=step.text,
                    query=step.query,
                    request=step.request,
                    target_id=step.target_id,
                    ref=step.ref,
                )
            except Exception as exc:  # pragma: no cover - defensive
                failure = ExternalReplayFailure(
                    scenario_id=scenario.scenario_id,
                    step_index=step_index,
                    operation=step.operation,
                    reason="exception",
                    details=str(exc),
                )
                break
            retries += int(payload.get("retry_count") or 0)
            if not bool(payload.get("success")):
                failure = ExternalReplayFailure(
                    scenario_id=scenario.scenario_id,
                    step_index=step_index,
                    operation=step.operation,
                    reason="operation_failed",
                    details=str(payload.get("error") or ""),
                )
                break
            expects = _normalize_expectation(step.expect_contains)
            if expects:
                joined = _collect_payload_text(payload).casefold()
                missing = [item for item in expects if item.casefold() not in joined]
                if missing:
                    failure = ExternalReplayFailure(
                        scenario_id=scenario.scenario_id,
                        step_index=step_index,
                        operation=step.operation,
                        reason="expectation_mismatch",
                        details=", ".join(missing),
                    )
                    break
            completed_steps += 1
            report.completed_steps += 1

        duration_ms = (time.perf_counter() - started) * 1000.0
        success = failure is None
        if success:
            report.passed_scenarios += 1
        else:
            report.failed_scenarios += 1
            report.failures.append(failure)
        report.total_retries += retries
        report.scenario_results.append(
            ExternalReplayScenarioResult(
                scenario_id=scenario.scenario_id,
                category=scenario.category,
                title=scenario.title,
                success=success,
                step_count=len(scenario.steps),
                completed_steps=completed_steps,
                duration_ms=duration_ms,
                retries=retries,
                failure=failure,
            )
        )
    return report


def render_external_replay_markdown(report: ExternalReplayReport) -> str:
    lines = [
        "# External Browser Replay Report",
        "",
        f"- generated_at: `{report.generated_at}`",
        f"- total_scenarios: `{report.total_scenarios}`",
        f"- passed_scenarios: `{report.passed_scenarios}`",
        f"- failed_scenarios: `{report.failed_scenarios}`",
        f"- success_rate: `{report.success_rate:.4f}`",
        f"- total_steps: `{report.total_steps}`",
        f"- completed_steps: `{report.completed_steps}`",
        f"- total_retries: `{report.total_retries}`",
        f"- p95_scenario_duration_ms: `{report.p95_scenario_duration_ms:.2f}`",
        "",
        "## Scenario Results",
        "",
        "| scenario_id | category | success | steps | completed | duration_ms | retries |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in report.scenario_results:
        lines.append(
            f"| {row.scenario_id} | {row.category} | {int(row.success)} | "
            f"{row.step_count} | {row.completed_steps} | {row.duration_ms:.2f} | {row.retries} |"
        )
    if report.failures:
        lines.extend(
            [
                "",
                "## Failures",
                "",
                "| scenario_id | step_index | operation | reason | details |",
                "|---|---:|---|---|---|",
            ]
        )
        for item in report.failures:
            details = (item.details or "").replace("\n", " ").strip()
            lines.append(
                f"| {item.scenario_id} | {item.step_index} | {item.operation} | {item.reason} | {details} |"
            )
    return "\n".join(lines) + "\n"
