from __future__ import annotations

import asyncio
import queue
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
from uuid import uuid4

from aeiva.command.command_utils import build_runtime_async
from aeiva.event.event_names import EventNames
from aeiva.interface.gateway_base import ResponseQueueGateway
from aeiva.interface.progress_hints import build_progress_hint
from aeiva.util.file_utils import from_json_or_yaml


@dataclass(frozen=True)
class DialogueExpectation:
    contains_all: tuple[str, ...] = ()
    contains_any: tuple[str, ...] = ()
    excludes: tuple[str, ...] = ()
    min_response_chars: int = 1
    max_latency_seconds: Optional[float] = None
    metaui_min_sessions: Optional[int] = None
    metaui_require_non_empty_components: bool = False

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "DialogueExpectation":
        def _as_tuple(value: Any) -> tuple[str, ...]:
            if value is None:
                return ()
            if isinstance(value, str):
                token = value.strip()
                return (token,) if token else ()
            if isinstance(value, Sequence):
                out: list[str] = []
                for item in value:
                    token = str(item or "").strip()
                    if token:
                        out.append(token)
                return tuple(out)
            return ()

        max_latency: Optional[float] = None
        if raw.get("max_latency_seconds") is not None:
            try:
                parsed = float(raw.get("max_latency_seconds"))
                if parsed > 0:
                    max_latency = parsed
            except Exception:
                max_latency = None

        min_chars = 1
        try:
            min_chars = max(0, int(raw.get("min_response_chars", 1)))
        except Exception:
            min_chars = 1

        metaui_min_sessions: Optional[int] = None
        if raw.get("metaui_min_sessions") is not None:
            try:
                parsed = int(raw.get("metaui_min_sessions"))
                if parsed >= 0:
                    metaui_min_sessions = parsed
            except Exception:
                metaui_min_sessions = None

        return cls(
            contains_all=_as_tuple(raw.get("contains_all")),
            contains_any=_as_tuple(raw.get("contains_any")),
            excludes=_as_tuple(raw.get("excludes")),
            min_response_chars=min_chars,
            max_latency_seconds=max_latency,
            metaui_min_sessions=metaui_min_sessions,
            metaui_require_non_empty_components=bool(
                raw.get("metaui_require_non_empty_components", False)
            ),
        )


@dataclass(frozen=True)
class DialogueTurn:
    user: str
    timeout_seconds: float = 120.0
    expectation: DialogueExpectation = field(default_factory=DialogueExpectation)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "DialogueTurn":
        user = str(raw.get("user") or "").strip()
        if not user:
            raise ValueError("dialogue turn requires non-empty `user`.")
        timeout_seconds = 120.0
        if raw.get("timeout_seconds") is not None:
            try:
                timeout_seconds = max(1.0, float(raw.get("timeout_seconds")))
            except Exception:
                timeout_seconds = 120.0
        expectation_raw = raw.get("expectation")
        expectation = (
            DialogueExpectation.from_mapping(expectation_raw)
            if isinstance(expectation_raw, Mapping)
            else DialogueExpectation()
        )
        return cls(
            user=user,
            timeout_seconds=timeout_seconds,
            expectation=expectation,
        )


@dataclass(frozen=True)
class DialogueScenario:
    scenario_id: str
    description: str
    turns: tuple[DialogueTurn, ...]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "DialogueScenario":
        scenario_id = str(raw.get("id") or "").strip()
        if not scenario_id:
            raise ValueError("dialogue scenario requires non-empty `id`.")
        description = str(raw.get("description") or "").strip()
        turns_raw = raw.get("turns")
        if not isinstance(turns_raw, Sequence) or not turns_raw:
            raise ValueError(f"scenario '{scenario_id}' requires non-empty `turns` list.")
        turns: list[DialogueTurn] = []
        for item in turns_raw:
            if not isinstance(item, Mapping):
                raise ValueError(f"scenario '{scenario_id}' has non-object turn item.")
            turns.append(DialogueTurn.from_mapping(item))
        return cls(
            scenario_id=scenario_id,
            description=description,
            turns=tuple(turns),
        )


def load_dialogue_scenarios(raw: Mapping[str, Any]) -> list[DialogueScenario]:
    scenarios_raw = raw.get("scenarios")
    if not isinstance(scenarios_raw, Sequence) or not scenarios_raw:
        raise ValueError("scenario file requires non-empty `scenarios` list.")
    scenarios: list[DialogueScenario] = []
    seen: set[str] = set()
    for item in scenarios_raw:
        if not isinstance(item, Mapping):
            raise ValueError("scenario entry must be an object.")
        scenario = DialogueScenario.from_mapping(item)
        if scenario.scenario_id in seen:
            raise ValueError(f"duplicate scenario id: {scenario.scenario_id}")
        seen.add(scenario.scenario_id)
        scenarios.append(scenario)
    return scenarios


def load_dialogue_scenarios_from_file(path: str | Path) -> list[DialogueScenario]:
    """Load dialogue replay scenarios from a JSON/YAML file."""
    payload = from_json_or_yaml(str(path))
    if not isinstance(payload, Mapping):
        raise ValueError(f"scenario file must contain a mapping root: {path}")
    return load_dialogue_scenarios(payload)


@dataclass(frozen=True)
class MetaUISnapshot:
    available: bool
    connected_clients: int
    session_count: int
    component_counts: Dict[str, int]


@dataclass(frozen=True)
class DialogueTurnResult:
    user: str
    response: str
    latency_seconds: float
    hints: tuple[str, ...]
    timed_out: bool
    metaui: Optional[MetaUISnapshot]


@dataclass(frozen=True)
class DialogueScenarioResult:
    scenario_id: str
    passed: bool
    turns: tuple[DialogueTurnResult, ...]
    errors: tuple[str, ...]


@dataclass(frozen=True)
class DialogueReplayReport:
    generated_at: str
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    total_turns: int
    timed_out_turns: int
    avg_latency_seconds: float
    scenario_results: tuple[DialogueScenarioResult, ...]
    errors: tuple[str, ...]

    @property
    def success_rate(self) -> float:
        if self.total_scenarios <= 0:
            return 0.0
        return self.passed_scenarios / float(self.total_scenarios)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_scenarios": self.total_scenarios,
            "passed_scenarios": self.passed_scenarios,
            "failed_scenarios": self.failed_scenarios,
            "success_rate": self.success_rate,
            "total_turns": self.total_turns,
            "timed_out_turns": self.timed_out_turns,
            "avg_latency_seconds": self.avg_latency_seconds,
            "errors": list(self.errors),
            "scenario_results": [
                {
                    "scenario_id": item.scenario_id,
                    "passed": item.passed,
                    "errors": list(item.errors),
                    "turns": [
                        {
                            "user": turn.user,
                            "response": turn.response,
                            "latency_seconds": turn.latency_seconds,
                            "hints": list(turn.hints),
                            "timed_out": turn.timed_out,
                            "metaui": (
                                {
                                    "available": turn.metaui.available,
                                    "connected_clients": turn.metaui.connected_clients,
                                    "session_count": turn.metaui.session_count,
                                    "component_counts": dict(turn.metaui.component_counts),
                                }
                                if turn.metaui is not None
                                else None
                            ),
                        }
                        for turn in item.turns
                    ],
                }
                for item in self.scenario_results
            ],
        }


def _start_metaui_event_bridge_or_none(
    *,
    config_dict: Mapping[str, Any],
    queue_gateway: ResponseQueueGateway,
    agent_loop_getter: Any,
    route_token: str,
) -> Any:
    try:
        from aeiva.metaui.event_bridge import start_metaui_event_bridge

        return start_metaui_event_bridge(
            config_dict=config_dict,
            queue_gateway=queue_gateway,
            agent_loop_getter=agent_loop_getter,
            route_token=route_token,
        )
    except Exception:
        return None


def _get_metaui_orchestrator_or_none() -> Any:
    try:
        from aeiva.metaui.orchestrator import get_metaui_orchestrator

        return get_metaui_orchestrator()
    except Exception:
        return None


class GatewayDialogueReplay:
    """
    Run multi-turn dialogue replays against the real AEIVA runtime pipeline.

    This runner avoids manual UI operations by using the same queue-based
    gateway path that Gradio uses (Signal -> perception.stimuli -> response queue).
    """

    def __init__(
        self,
        *,
        config_dict: Mapping[str, Any],
        runtime: Any,
        agent: Any,
        route_token: str = "gradio",
    ) -> None:
        self._config_dict = dict(config_dict)
        self._runtime = runtime
        self._agent = agent
        self._route_token = route_token
        self._response_queue: queue.Queue = queue.Queue()
        gateway_cfg = dict(self._config_dict.get("gradio_config") or {})
        llm_timeout = float(
            (self._config_dict.get("llm_gateway_config") or {}).get("llm_timeout", 60.0)
        )
        self._queue_gateway = ResponseQueueGateway(
            gateway_cfg,
            self._agent.event_bus,
            self._response_queue,
            response_timeout=llm_timeout,
            require_route=True,
        )
        self._queue_gateway.register_handlers()
        self._metaui_bridge = None
        self._runtime_task: Optional[asyncio.Task] = None
        self._started = False

    @classmethod
    async def from_config(
        cls,
        *,
        config_dict: Mapping[str, Any],
        route_token: str = "gradio",
    ) -> "GatewayDialogueReplay":
        runtime, agent = await build_runtime_async(dict(config_dict))
        runner = cls(
            config_dict=config_dict,
            runtime=runtime,
            agent=agent,
            route_token=route_token,
        )
        await runner.start()
        return runner

    async def start(self) -> None:
        if self._started:
            return
        self._metaui_bridge = _start_metaui_event_bridge_or_none(
            config_dict=self._config_dict,
            queue_gateway=self._queue_gateway,
            agent_loop_getter=lambda: getattr(
                getattr(self._agent, "event_bus", None), "loop", None
            ),
            route_token=self._route_token,
        )
        session_payload = {"session_id": uuid4().hex}
        self._runtime_task = asyncio.create_task(
            self._runtime.run(raw_memory_session=session_payload)
        )
        await self._wait_for_agent_loop_ready(timeout_seconds=8.0)
        self._started = True

    async def stop(self) -> None:
        if not self._started:
            return
        if self._metaui_bridge is not None:
            self._metaui_bridge.stop(timeout=1.5)
        self._runtime.request_stop()
        task = self._runtime_task
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=8.0)
            except asyncio.TimeoutError:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        self._runtime_task = None
        self._started = False

    async def __aenter__(self) -> "GatewayDialogueReplay":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()

    async def _wait_for_agent_loop_ready(self, *, timeout_seconds: float) -> None:
        deadline = time.monotonic() + max(0.1, float(timeout_seconds))
        while time.monotonic() < deadline:
            loop = getattr(getattr(self._agent, "event_bus", None), "loop", None)
            if loop is not None:
                return
            await asyncio.sleep(0.05)
        raise TimeoutError("Agent event loop did not become ready in time.")

    def _progress_hint(self, *, elapsed_seconds: float, hint_index: int) -> str:
        return build_progress_hint(
            elapsed_seconds=elapsed_seconds,
            hint_index=hint_index,
            phases=(
                "Thinking",
                "Acting",
                "Waiting for tools",
                "Retrying if needed",
                "Still working",
            ),
        )

    async def send_turn(
        self,
        *,
        user_input: str,
        timeout_seconds: float,
    ) -> DialogueTurnResult:
        if not self._started:
            raise RuntimeError("GatewayDialogueReplay must be started before sending turns.")

        signal = self._queue_gateway.build_input_signal(
            user_input,
            source=EventNames.PERCEPTION_GRADIO,
            route=self._route_token,
        )
        trace_id = signal.trace_id
        await self._queue_gateway.emit_input(
            signal,
            route=self._route_token,
            add_pending_route=True,
            event_name=EventNames.PERCEPTION_STIMULI,
        )

        llm_stream = bool(
            (self._config_dict.get("llm_gateway_config") or {}).get("llm_stream", False)
        )
        gradio_cfg = self._config_dict.get("gradio_config") or {}
        hint_interval = float(gradio_cfg.get("progress_hint_interval", 4.0))
        poll_timeout = float(gradio_cfg.get("progress_poll_timeout", 0.8))
        deadline = time.monotonic() + max(1.0, float(timeout_seconds))
        started = time.monotonic()
        next_hint_at = started
        hint_index = 0
        hints: list[str] = []
        chunks: list[str] = []
        response = ""
        timed_out = False

        while True:
            now = time.monotonic()
            remaining = deadline - now
            if remaining <= 0:
                timed_out = True
                if not response:
                    response = "I'm sorry, I didn't receive a response in time."
                break
            try:
                payload = await asyncio.to_thread(
                    self._queue_gateway.get_for_trace,
                    trace_id,
                    min(max(0.05, poll_timeout), remaining),
                )
                if llm_stream:
                    if payload == "<END_OF_RESPONSE>":
                        break
                    chunks.append(str(payload))
                else:
                    response = str(payload)
                    break
            except queue.Empty:
                now = time.monotonic()
                if now >= next_hint_at:
                    hints.append(
                        self._progress_hint(
                            elapsed_seconds=now - started,
                            hint_index=hint_index,
                        )
                    )
                    hint_index += 1
                    next_hint_at = now + max(0.1, hint_interval)

        if llm_stream:
            response = "".join(chunks)
            if not response and not timed_out:
                response = ""

        metaui_snapshot = await self._collect_metaui_snapshot()
        return DialogueTurnResult(
            user=user_input,
            response=response,
            latency_seconds=max(0.0, time.monotonic() - started),
            hints=tuple(hints),
            timed_out=timed_out,
            metaui=metaui_snapshot,
        )

    async def _collect_metaui_snapshot(self) -> Optional[MetaUISnapshot]:
        orchestrator = _get_metaui_orchestrator_or_none()
        if orchestrator is None:
            return None
        try:
            status = await orchestrator.status()
            sessions_resp = await orchestrator.list_sessions()
        except Exception:
            return None

        if not isinstance(status, Mapping) or not isinstance(sessions_resp, Mapping):
            return None
        sessions = sessions_resp.get("sessions")
        if not isinstance(sessions, Sequence):
            sessions = []
        component_counts: Dict[str, int] = {}
        for item in sessions:
            if not isinstance(item, Mapping):
                continue
            ui_id = str(item.get("ui_id") or "").strip()
            if not ui_id:
                continue
            try:
                session_payload = await orchestrator.get_session(ui_id)
            except Exception:
                continue
            spec = session_payload.get("spec") if isinstance(session_payload, Mapping) else None
            components = spec.get("components") if isinstance(spec, Mapping) else None
            component_counts[ui_id] = len(components) if isinstance(components, Sequence) else 0

        return MetaUISnapshot(
            available=True,
            connected_clients=int(status.get("connected_clients") or 0),
            session_count=len(sessions),
            component_counts=component_counts,
        )

    async def run_scenario(
        self,
        scenario: DialogueScenario,
        *,
        fail_fast: bool = False,
    ) -> DialogueScenarioResult:
        turn_results: list[DialogueTurnResult] = []
        errors: list[str] = []
        for index, turn in enumerate(scenario.turns):
            result = await self.send_turn(
                user_input=turn.user,
                timeout_seconds=turn.timeout_seconds,
            )
            turn_results.append(result)
            turn_errors = validate_turn_expectation(
                scenario_id=scenario.scenario_id,
                turn_index=index,
                result=result,
                expectation=turn.expectation,
            )
            errors.extend(turn_errors)
            if fail_fast and turn_errors:
                break
        return DialogueScenarioResult(
            scenario_id=scenario.scenario_id,
            passed=not errors,
            turns=tuple(turn_results),
            errors=tuple(errors),
        )


def validate_turn_expectation(
    *,
    scenario_id: str,
    turn_index: int,
    result: DialogueTurnResult,
    expectation: DialogueExpectation,
) -> list[str]:
    errors: list[str] = []
    response = result.response or ""
    if len(response) < expectation.min_response_chars:
        errors.append(
            f"{scenario_id}/turn[{turn_index}] response too short: {len(response)} < {expectation.min_response_chars}"
        )
    if (
        expectation.max_latency_seconds is not None
        and result.latency_seconds > expectation.max_latency_seconds
    ):
        errors.append(
            f"{scenario_id}/turn[{turn_index}] latency {result.latency_seconds:.2f}s > {expectation.max_latency_seconds:.2f}s"
        )
    for token in expectation.contains_all:
        if token not in response:
            errors.append(
                f"{scenario_id}/turn[{turn_index}] missing required token: {token!r}"
            )
    if expectation.contains_any and not any(
        token in response for token in expectation.contains_any
    ):
        errors.append(
            f"{scenario_id}/turn[{turn_index}] none of contains_any matched: {list(expectation.contains_any)}"
        )
    for token in expectation.excludes:
        if token in response:
            errors.append(
                f"{scenario_id}/turn[{turn_index}] response contains forbidden token: {token!r}"
            )

    if expectation.metaui_min_sessions is not None:
        snapshot = result.metaui
        if snapshot is None:
            errors.append(f"{scenario_id}/turn[{turn_index}] MetaUI snapshot unavailable.")
        elif snapshot.session_count < expectation.metaui_min_sessions:
            errors.append(
                f"{scenario_id}/turn[{turn_index}] MetaUI session_count {snapshot.session_count} "
                f"< required {expectation.metaui_min_sessions}"
            )

    if expectation.metaui_require_non_empty_components:
        snapshot = result.metaui
        if snapshot is None:
            errors.append(f"{scenario_id}/turn[{turn_index}] MetaUI snapshot unavailable.")
        elif not any(count > 0 for count in snapshot.component_counts.values()):
            errors.append(
                f"{scenario_id}/turn[{turn_index}] all MetaUI sessions have empty components."
            )
    return errors


def select_scenarios(
    scenarios: Sequence[DialogueScenario],
    *,
    scenario_ids: Optional[Iterable[str]] = None,
) -> list[DialogueScenario]:
    if not scenario_ids:
        return list(scenarios)
    required = {str(item).strip() for item in scenario_ids if str(item).strip()}
    selected = [scenario for scenario in scenarios if scenario.scenario_id in required]
    missing = sorted(required - {item.scenario_id for item in selected})
    if missing:
        raise ValueError(f"unknown scenario ids: {missing}")
    return selected


def build_dialogue_report(
    results: Sequence[DialogueScenarioResult],
) -> DialogueReplayReport:
    scenarios = tuple(results)
    total_scenarios = len(scenarios)
    passed_scenarios = sum(1 for item in scenarios if item.passed)
    failed_scenarios = total_scenarios - passed_scenarios
    turn_results = [turn for scenario in scenarios for turn in scenario.turns]
    total_turns = len(turn_results)
    timed_out_turns = sum(1 for turn in turn_results if turn.timed_out)
    avg_latency_seconds = (
        sum(turn.latency_seconds for turn in turn_results) / float(total_turns)
        if total_turns > 0
        else 0.0
    )
    errors: list[str] = []
    for scenario in scenarios:
        for err in scenario.errors:
            errors.append(f"[{scenario.scenario_id}] {err}")

    return DialogueReplayReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_scenarios=total_scenarios,
        passed_scenarios=passed_scenarios,
        failed_scenarios=failed_scenarios,
        total_turns=total_turns,
        timed_out_turns=timed_out_turns,
        avg_latency_seconds=avg_latency_seconds,
        scenario_results=scenarios,
        errors=tuple(errors),
    )


def render_dialogue_report_markdown(report: DialogueReplayReport) -> str:
    lines = [
        "# Dialogue Replay Report",
        "",
        f"- generated_at: `{report.generated_at}`",
        f"- total_scenarios: `{report.total_scenarios}`",
        f"- passed_scenarios: `{report.passed_scenarios}`",
        f"- failed_scenarios: `{report.failed_scenarios}`",
        f"- success_rate: `{report.success_rate:.4f}`",
        f"- total_turns: `{report.total_turns}`",
        f"- timed_out_turns: `{report.timed_out_turns}`",
        f"- avg_latency_seconds: `{report.avg_latency_seconds:.2f}`",
        "",
        "## Scenario Results",
        "",
        "| scenario_id | passed | turns | errors |",
        "|---|---:|---:|---:|",
    ]
    for result in report.scenario_results:
        lines.append(
            f"| {result.scenario_id} | {int(result.passed)} | "
            f"{len(result.turns)} | {len(result.errors)} |"
        )
    if report.errors:
        lines.extend(["", "## Errors", ""])
        lines.extend([f"- {item}" for item in report.errors])
    return "\n".join(lines) + "\n"
