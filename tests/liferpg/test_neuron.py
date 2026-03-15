from __future__ import annotations

import pytest

from aeiva.event.event_names import EventNames
from aeiva.liferpg.neuron import LifeRPGNeuron
from aeiva.neuron import Signal


pytest_plugins = ("pytest_asyncio",)


@pytest.mark.asyncio
async def test_liferpg_query_returns_current_state(tmp_path) -> None:
    neuron = LifeRPGNeuron(
        config={
            "base_dir": str(tmp_path / "liferpg"),
            "raw_memory_base_dir": str(tmp_path / "memory"),
            "enabled": True,
            "llm_gateway_config": {},
        }
    )
    await neuron.setup()

    result = await neuron.process(Signal(source=EventNames.LIFERPG_QUERY, data={}))

    assert result["type"] == "state"
    assert "profile" in result
    assert "roles" in result["profile"]


@pytest.mark.asyncio
async def test_liferpg_setup_applies_default_profile_from_config(tmp_path) -> None:
    neuron = LifeRPGNeuron(
        config={
            "base_dir": str(tmp_path / "liferpg"),
            "raw_memory_base_dir": str(tmp_path / "memory"),
            "enabled": True,
            "llm_gateway_config": {},
            "default_profile": {
                "user": {
                    "bio": {
                        "name": "Bang Liu",
                        "birth_date": "1993-07-18",
                        "primary_profession": "AI Engineer",
                    },
                    "identity": "Researcher and builder.",
                }
            },
        }
    )
    await neuron.setup()

    profile = neuron.store.read_profile()

    assert profile["user"]["bio"]["name"] == "Bang Liu"
    assert profile["user"]["bio"]["primary_profession"] == "AI Engineer"
    assert profile["user"]["identity"] == "Researcher and builder."


def test_liferpg_neuron_subscribes_only_to_active_update_sources() -> None:
    neuron = LifeRPGNeuron(config={})

    assert EventNames.RAW_MEMORY_SESSION_CLOSED in neuron.SUBSCRIPTIONS
    assert EventNames.LIFERPG_QUERY in neuron.SUBSCRIPTIONS
    assert EventNames.LIFERPG_UPDATE in neuron.SUBSCRIPTIONS
    assert EventNames.RAW_MEMORY_SUMMARY_REQUEST not in neuron.SUBSCRIPTIONS


@pytest.mark.asyncio
async def test_liferpg_session_review_applies_patch(tmp_path) -> None:
    neuron = LifeRPGNeuron(
        config={
            "base_dir": str(tmp_path / "liferpg"),
            "raw_memory_base_dir": str(tmp_path / "memory"),
            "enabled": True,
            "llm_gateway_config": {},
        }
    )
    await neuron.setup()

    async def _fake_decide_patch(*_args, **_kwargs):
        return {
            "update": True,
            "summary": "project created",
            "patch": {
                "projects": [
                    {
                        "title": "LifeRPG module",
                        "description": "Ship schema + panel",
                        "milestones": ["schema", "neuron", "ui"],
                        "deadline": "2026-03-20",
                        "status": "active",
                    }
                ]
            },
        }

    neuron._decide_patch = _fake_decide_patch  # type: ignore[method-assign]

    signal = Signal(
        source=EventNames.RAW_MEMORY_SESSION_CLOSED,
        data={
            "user_id": "User",
            "session_id": "sess-001",
            "session_text": "User wants to build LifeRPG module.",
            "end_time": "2026-03-14T14:00:00+00:00",
        },
    )

    result = await neuron.process(signal)

    assert result["updated"] is True
    assert result["period"] == "session"
    profile = neuron.store.read_profile()
    assert profile["projects"][0]["title"] == "LifeRPG module"


@pytest.mark.asyncio
async def test_liferpg_period_rollover_triggers_daily_review(tmp_path) -> None:
    neuron = LifeRPGNeuron(
        config={
            "base_dir": str(tmp_path / "liferpg"),
            "raw_memory_base_dir": str(tmp_path / "memory"),
            "enabled": True,
            "llm_gateway_config": {},
        }
    )
    await neuron.setup()

    periods: list[str] = []

    async def _fake_run_period_update(period: str, *_args, **_kwargs):
        periods.append(period)
        return {"updated": False, "period": period}

    neuron._run_period_update = _fake_run_period_update  # type: ignore[method-assign]

    first = Signal(
        source=EventNames.RAW_MEMORY_SESSION_CLOSED,
        data={
            "session_id": "sess-a",
            "session_text": "day1",
            "end_time": "2026-03-15T03:50:00+00:00",
        },
    )
    second = Signal(
        source=EventNames.RAW_MEMORY_SESSION_CLOSED,
        data={
            "session_id": "sess-b",
            "session_text": "day2",
            "end_time": "2026-03-15T05:10:00+00:00",
        },
    )

    await neuron.process(first)
    await neuron.process(second)

    assert periods.count("session") == 2
    assert "daily" in periods
