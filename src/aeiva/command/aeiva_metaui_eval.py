from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import click

from aeiva.command.command_utils import get_package_root
from aeiva.util.file_utils import from_json_or_yaml


PACKAGE_ROOT = get_package_root()
_json_config = PACKAGE_ROOT / "configs" / "agent_config.json"
_yaml_config = PACKAGE_ROOT / "configs" / "agent_config.yaml"
DEFAULT_CONFIG_PATH = _json_config if _json_config.exists() else _yaml_config
DEFAULT_SCENARIO_PATH = PACKAGE_ROOT / "docs" / "examples" / "dialogue_replay" / "metaui_dialogue_suite.yaml"
DEFAULT_PYTEST_TARGETS: tuple[str, ...] = (
    "tests/metaui",
    "tests/testing/test_dialogue_replay.py",
    "tests/command/test_dialogue_replay_command.py",
    "tests/command/test_gradio_progress_hints.py",
)
_REPLAY_DISABLED_SENSORS: frozenset[str] = frozenset({"percept_terminal_input"})
_REPLAY_DISABLED_NEURON_CONFIGS: frozenset[str] = frozenset(
    {
        "memory_config",
        "raw_memory_config",
        "raw_memory_summary_config",
        "emotion_config",
        "goal_config",
        "world_model_config",
    }
)
_REPLAY_ONLY_TOOLS: tuple[str, ...] = ("metaui",)
_REPLAY_MAX_OUTPUT_TOKENS = 1800


@dataclass(frozen=True)
class EvalStepResult:
    name: str
    status: str
    duration_seconds: float
    return_code: int
    command: tuple[str, ...]
    stdout_tail: str
    stderr_tail: str
    reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "duration_seconds": self.duration_seconds,
            "return_code": self.return_code,
            "command": list(self.command),
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class EvalReport:
    generated_at: str
    replay_mode: str
    python_executable: str
    steps: tuple[EvalStepResult, ...]

    @property
    def passed_steps(self) -> int:
        return sum(1 for item in self.steps if item.status == "passed")

    @property
    def failed_steps(self) -> int:
        return sum(1 for item in self.steps if item.status == "failed")

    @property
    def skipped_steps(self) -> int:
        return sum(1 for item in self.steps if item.status == "skipped")

    @property
    def success(self) -> bool:
        return self.failed_steps == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "replay_mode": self.replay_mode,
            "python_executable": self.python_executable,
            "success": self.success,
            "passed_steps": self.passed_steps,
            "failed_steps": self.failed_steps,
            "skipped_steps": self.skipped_steps,
            "steps": [item.to_dict() for item in self.steps],
        }


def _tail(text: str, *, max_lines: int = 40) -> str:
    lines = (text or "").splitlines()
    if len(lines) <= max_lines:
        return text or ""
    return "\n".join(lines[-max_lines:])


def _write_text(path: Optional[str], content: str) -> None:
    if not path:
        return
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")


def _build_replay_config_payload(config_path: str) -> dict[str, Any]:
    raw = from_json_or_yaml(config_path)
    if not isinstance(raw, dict):
        raise ValueError(f"Config must be a mapping: {config_path}")
    payload = copy.deepcopy(raw)
    perception_cfg = payload.get("perception_config")
    if not isinstance(perception_cfg, dict):
        return payload
    sensors = perception_cfg.get("sensors")
    if not isinstance(sensors, list):
        return payload
    filtered: list[Any] = []
    for sensor in sensors:
        if not isinstance(sensor, dict):
            filtered.append(sensor)
            continue
        name = str(sensor.get("sensor_name") or "").strip().lower()
        if name in _REPLAY_DISABLED_SENSORS:
            continue
        filtered.append(sensor)
    perception_cfg["sensors"] = filtered

    for key in _REPLAY_DISABLED_NEURON_CONFIGS:
        cfg = payload.get(key)
        if not isinstance(cfg, dict):
            cfg = {}
            payload[key] = cfg
        cfg["enabled"] = False

    action_cfg = payload.get("action_config")
    if not isinstance(action_cfg, dict):
        action_cfg = {}
        payload["action_config"] = action_cfg
    action_cfg["tools"] = list(_REPLAY_ONLY_TOOLS)

    llm_cfg = payload.get("llm_gateway_config")
    if not isinstance(llm_cfg, dict):
        llm_cfg = {}
        payload["llm_gateway_config"] = llm_cfg
    llm_cfg["llm_stream"] = False
    llm_cfg["llm_use_async"] = True
    llm_cfg["llm_tool_choice"] = "required"
    raw_max_tokens = llm_cfg.get("llm_max_output_tokens")
    try:
        parsed_tokens = int(raw_max_tokens)
    except Exception:
        parsed_tokens = _REPLAY_MAX_OUTPUT_TOKENS
    llm_cfg["llm_max_output_tokens"] = max(
        256,
        min(parsed_tokens, _REPLAY_MAX_OUTPUT_TOKENS),
    )
    return payload


def _write_temp_replay_config(payload: dict[str, Any]) -> str:
    fd, path = tempfile.mkstemp(prefix="aeiva-metaui-replay-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


def _config_has_live_credentials(config_path: str) -> bool:
    try:
        config = from_json_or_yaml(config_path)
    except Exception:
        return bool(os.getenv("OPENAI_API_KEY"))

    llm_cfg = config.get("llm_gateway_config") if isinstance(config, dict) else {}
    if not isinstance(llm_cfg, dict):
        llm_cfg = {}

    direct_key = str(llm_cfg.get("llm_api_key") or "").strip()
    if direct_key:
        return True

    env_var = str(llm_cfg.get("llm_api_key_env_var") or "").strip()
    if env_var and os.getenv(env_var):
        return True

    return bool(os.getenv("OPENAI_API_KEY"))


def _should_run_live_replay(*, replay_mode: str, has_credentials: bool) -> bool:
    mode = str(replay_mode or "auto").strip().lower()
    if mode == "off":
        return False
    if mode == "required":
        return True
    return bool(has_credentials)


def _probe_connectivity_url(config_path: str) -> str:
    try:
        config = from_json_or_yaml(config_path)
    except Exception:
        return "https://api.openai.com/v1/models"
    llm_cfg = config.get("llm_gateway_config") if isinstance(config, dict) else {}
    if not isinstance(llm_cfg, dict):
        llm_cfg = {}
    base = str(
        llm_cfg.get("llm_api_base")
        or llm_cfg.get("api_base")
        or llm_cfg.get("base_url")
        or ""
    ).strip()
    if not base:
        return "https://api.openai.com/v1/models"
    if "://" not in base:
        base = f"https://{base}"
    parsed = urlparse(base)
    root = base.rstrip("/")
    if parsed.path and parsed.path not in ("", "/"):
        return root
    return f"{root}/v1/models"


def _resolve_llm_auth(config_path: str) -> tuple[str, str]:
    try:
        config = from_json_or_yaml(config_path)
    except Exception:
        return ("https://api.openai.com/v1/models", "")
    llm_cfg = config.get("llm_gateway_config") if isinstance(config, dict) else {}
    if not isinstance(llm_cfg, dict):
        llm_cfg = {}

    api_key = str(llm_cfg.get("llm_api_key") or "").strip()
    env_var = str(llm_cfg.get("llm_api_key_env_var") or "").strip()
    if not api_key and env_var:
        api_key = str(os.getenv(env_var) or "").strip()
    if not api_key:
        api_key = str(os.getenv("OPENAI_API_KEY") or "").strip()

    probe_url = _probe_connectivity_url(config_path)
    return (probe_url, api_key)


def _has_live_replay_connectivity(config_path: str, *, timeout_seconds: float = 2.0) -> bool:
    probe_url = _probe_connectivity_url(config_path)
    timeout = max(0.2, float(timeout_seconds))
    def _probe_once() -> bool:
        try:
            request = Request(probe_url, method="HEAD")
            with urlopen(request, timeout=timeout):
                return True
        except HTTPError:
            # HTTP-level failures (401/403/404/etc.) still prove reachability.
            return True
        except URLError:
            return False
        except OSError:
            return False
        except Exception:
            try:
                request = Request(probe_url, method="GET")
                with urlopen(request, timeout=timeout):
                    return True
            except HTTPError:
                return True
            except Exception:
                return False

    # Require two consecutive successes to reduce false positives on flaky networks.
    return _probe_once() and _probe_once()


def _has_live_replay_llm_readiness(config_path: str, *, timeout_seconds: float = 3.0) -> bool:
    probe_url, api_key = _resolve_llm_auth(config_path)
    if not api_key:
        return False
    headers = {"Authorization": f"Bearer {api_key}"}
    timeout = max(0.2, float(timeout_seconds))
    request = Request(probe_url, method="GET", headers=headers)
    try:
        with urlopen(request, timeout=timeout):
            return True
    except HTTPError as exc:
        if exc.code in (401, 403):
            return False
        if exc.code in (404, 405):
            # Endpoint may differ across providers; keep auto mode permissive.
            return True
        return False
    except Exception:
        return False


def _execute_step(
    *,
    name: str,
    command: Sequence[str],
    timeout_seconds: float,
) -> EvalStepResult:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            timeout=max(1.0, float(timeout_seconds)),
        )
        duration = max(0.0, time.monotonic() - started)
        return EvalStepResult(
            name=name,
            status="passed" if completed.returncode == 0 else "failed",
            duration_seconds=duration,
            return_code=int(completed.returncode),
            command=tuple(command),
            stdout_tail=_tail(completed.stdout),
            stderr_tail=_tail(completed.stderr),
        )
    except subprocess.TimeoutExpired as exc:
        duration = max(0.0, time.monotonic() - started)
        return EvalStepResult(
            name=name,
            status="failed",
            duration_seconds=duration,
            return_code=-1,
            command=tuple(command),
            stdout_tail=_tail(exc.stdout or ""),
            stderr_tail=_tail(exc.stderr or ""),
            reason=f"timeout>{timeout_seconds:.1f}s",
        )


def _render_markdown(report: EvalReport) -> str:
    lines = [
        "# MetaUI Evaluation Report",
        "",
        f"- generated_at: `{report.generated_at}`",
        f"- replay_mode: `{report.replay_mode}`",
        f"- python_executable: `{report.python_executable}`",
        f"- success: `{int(report.success)}`",
        f"- passed_steps: `{report.passed_steps}`",
        f"- failed_steps: `{report.failed_steps}`",
        f"- skipped_steps: `{report.skipped_steps}`",
        "",
        "## Steps",
        "",
        "| name | status | duration_s | return_code |",
        "|---|---|---:|---:|",
    ]
    for step in report.steps:
        lines.append(
            f"| {step.name} | {step.status} | {step.duration_seconds:.2f} | {step.return_code} |"
        )
    failures = [item for item in report.steps if item.status == "failed"]
    if failures:
        lines.extend(["", "## Failures", ""])
        for step in failures:
            lines.append(f"### {step.name}")
            if step.reason:
                lines.append(f"- reason: `{step.reason}`")
            lines.append("")
            if step.stderr_tail.strip():
                lines.append("```text")
                lines.append(step.stderr_tail)
                lines.append("```")
            elif step.stdout_tail.strip():
                lines.append("```text")
                lines.append(step.stdout_tail)
                lines.append("```")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _build_skipped_step(name: str, reason: str) -> EvalStepResult:
    return EvalStepResult(
        name=name,
        status="skipped",
        duration_seconds=0.0,
        return_code=0,
        command=(),
        stdout_tail="",
        stderr_tail="",
        reason=reason,
    )


@click.command(name="aeiva-metaui-eval")
@click.option(
    "--config",
    "-c",
    default=str(DEFAULT_CONFIG_PATH),
    type=click.Path(exists=True, dir_okay=False),
    help="AEIVA runtime config used for live dialogue replay.",
)
@click.option(
    "--replay-scenarios",
    default=str(DEFAULT_SCENARIO_PATH),
    type=click.Path(exists=True, dir_okay=False),
    help="Scenario file for live dialogue replay evaluation.",
)
@click.option(
    "--replay-mode",
    type=click.Choice(["auto", "required", "off"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="Live replay execution mode.",
)
@click.option(
    "--pytest-target",
    "pytest_targets",
    multiple=True,
    help="Additional/override pytest targets. Defaults to MetaUI core suites.",
)
@click.option(
    "--python-exec",
    default=sys.executable,
    show_default=True,
    help="Python executable used to run subprocess test commands.",
)
@click.option(
    "--pytest-timeout",
    default=600.0,
    show_default=True,
    type=float,
    help="Timeout (seconds) for pytest step.",
)
@click.option(
    "--replay-timeout",
    default=240.0,
    show_default=True,
    type=float,
    help="Timeout (seconds) for live replay step.",
)
@click.option(
    "--replay-scenario-id",
    "replay_scenario_ids",
    multiple=True,
    help="Limit live replay to selected scenario id(s). Can be repeated.",
)
@click.option(
    "--replay-fail-fast/--no-replay-fail-fast",
    default=True,
    show_default=True,
    help="Stop each replay scenario at first failing turn expectation.",
)
@click.option(
    "--output-json",
    default=".reports/metaui-evaluation.json",
    show_default=True,
    type=click.Path(dir_okay=False),
    help="JSON report output path.",
)
@click.option(
    "--output-md",
    default=".reports/metaui-evaluation.md",
    show_default=True,
    type=click.Path(dir_okay=False),
    help="Markdown report output path.",
)
@click.option("--verbose", "-v", is_flag=True, help="Print each executed command.")
def run(
    config: str,
    replay_scenarios: str,
    replay_mode: str,
    pytest_targets: Sequence[str],
    python_exec: str,
    pytest_timeout: float,
    replay_timeout: float,
    replay_scenario_ids: Sequence[str],
    replay_fail_fast: bool,
    output_json: str,
    output_md: str,
    verbose: bool,
) -> None:
    resolved_targets = tuple(pytest_targets) if pytest_targets else DEFAULT_PYTEST_TARGETS
    steps: list[EvalStepResult] = []
    replay_temp_config_path: Optional[str] = None

    try:
        pytest_cmd = [python_exec, "-m", "pytest", "-q", *resolved_targets]
        if verbose:
            click.echo(f"[metaui-eval] running pytest step: {' '.join(pytest_cmd)}")
        steps.append(
            _execute_step(
                name="metaui_pytest",
                command=pytest_cmd,
                timeout_seconds=pytest_timeout,
            )
        )

        has_credentials = _config_has_live_credentials(config)
        run_live_requested = _should_run_live_replay(
            replay_mode=replay_mode,
            has_credentials=has_credentials,
        )
        replay_mode_normalized = str(replay_mode).strip().lower()
        connectivity_ok = True
        llm_ready = True
        if replay_mode_normalized == "auto" and run_live_requested:
            connectivity_ok = _has_live_replay_connectivity(config)
            llm_ready = _has_live_replay_llm_readiness(config)
        run_live = bool(run_live_requested and connectivity_ok and llm_ready)
        if verbose:
            click.echo(
                "[metaui-eval] preflight "
                f"credentials={int(has_credentials)} "
                f"run_live_requested={int(run_live_requested)} "
                f"connectivity_ok={int(connectivity_ok)} "
                f"llm_ready={int(llm_ready)} "
                f"run_live={int(run_live)}"
            )

        if run_live:
            replay_config = config
            try:
                replay_payload = _build_replay_config_payload(config)
                replay_temp_config_path = _write_temp_replay_config(replay_payload)
                replay_config = replay_temp_config_path
            except Exception:
                replay_config = config

            replay_cmd = [
                python_exec,
                "-m",
                "aeiva.command.aeiva_dialogue_replay",
                "--config",
                replay_config,
                "--scenarios",
                replay_scenarios,
                "--output-json",
                str(Path(output_json).with_suffix(".replay.json")),
                "--output-md",
                str(Path(output_md).with_suffix(".replay.md")),
            ]
            for scenario_id in replay_scenario_ids:
                token = str(scenario_id).strip()
                if token:
                    replay_cmd.extend(["--scenario-id", token])
            if replay_fail_fast:
                replay_cmd.append("--fail-fast")
            if verbose:
                click.echo(f"[metaui-eval] running replay step: {' '.join(replay_cmd)}")
            steps.append(
                _execute_step(
                    name="metaui_live_replay",
                    command=replay_cmd,
                    timeout_seconds=replay_timeout,
                )
            )
        else:
            if replay_mode_normalized == "off":
                reason = "replay disabled by --replay-mode=off"
            elif run_live_requested and not connectivity_ok:
                reason = "replay skipped in auto mode: LLM endpoint not reachable"
            elif run_live_requested and not llm_ready:
                reason = "replay skipped in auto mode: LLM credentials not ready"
            else:
                reason = "replay skipped in auto mode: no live LLM credentials detected"
            steps.append(_build_skipped_step("metaui_live_replay", reason))

        report = EvalReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            replay_mode=replay_mode_normalized,
            python_executable=python_exec,
            steps=tuple(steps),
        )

        _write_text(output_json, json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n")
        _write_text(output_md, _render_markdown(report))

        click.echo(f"success: {int(report.success)}")
        click.echo(f"passed_steps: {report.passed_steps}")
        click.echo(f"failed_steps: {report.failed_steps}")
        click.echo(f"skipped_steps: {report.skipped_steps}")
        for step in report.steps:
            click.echo(f"- {step.name}: {step.status} ({step.duration_seconds:.2f}s)")

        if not report.success:
            raise SystemExit(1)
    finally:
        if replay_temp_config_path:
            try:
                Path(replay_temp_config_path).unlink(missing_ok=True)
            except Exception:
                pass


if __name__ == "__main__":
    run()
