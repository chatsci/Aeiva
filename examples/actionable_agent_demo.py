#!/usr/bin/env python3
"""
AEIVA Agent Demo - action-capable, event-driven pipeline.

Usage:
    python examples/actionable_agent_demo.py

Or with a specific task:
    python examples/actionable_agent_demo.py "List files in current directory"
"""

import asyncio
import sys
import os
import queue
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from aeiva.agent.agent import Agent
from aeiva.command.command_utils import resolve_env_vars
from aeiva.interface.gateway_base import ResponseQueueGateway
from aeiva.event.event_names import EventNames


async def interactive_mode():
    """Run agent in interactive mode."""
    print("=" * 60)
    print("AEIVA Agent - Event-Driven Assistant")
    print("=" * 60)
    print()
    print("Commands:")
    print("  Type your task and press Enter")
    print("  'reset' - Clear conversation history")
    print("  'quit'  - Exit")
    print()

    cfg_path = os.path.join(os.path.dirname(__file__), "..", "configs", "agent_config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    resolve_env_vars(config)
    config.setdefault("agent_config", {})["ui_enabled"] = False
    config.setdefault("perception_config", {})["sensors"] = []

    agent = Agent(config)
    await agent.setup_async()

    response_queue = queue.Queue()
    terminal_cfg = config.get("terminal_config") or {}
    response_timeout = float((config.get("llm_gateway_config") or {}).get("llm_timeout", 60.0))
    gateway = ResponseQueueGateway(terminal_cfg, agent.event_bus, response_queue, response_timeout=response_timeout)
    gateway.register_handlers()

    agent_task = asyncio.create_task(agent.run())

    model_name = (config.get("llm_gateway_config") or {}).get("llm_model_name", "unknown")
    print(f"Model: {model_name}")
    print("-" * 60)
    print()

    while True:
        try:
            task = input("You: ").strip()

            if not task:
                continue

            if task.lower() == "quit":
                print("Goodbye!")
                break

            if task.lower() == "reset":
                agent.cognition.state.clear_history()
                print("Conversation reset.\n")
                continue

            # Run the agent
            print("\n[Working...]\n")
            signal = gateway.build_input_signal(
                task,
                source=EventNames.PERCEPTION_TERMINAL,
                meta={"llm_stream": False},
            )
            trace_id = signal.trace_id
            await gateway.emit_input(
                signal,
                event_name=EventNames.PERCEPTION_STIMULI,
                await_response=False,
            )
            response = gateway.get_for_trace(trace_id, response_timeout)
            print(f"Agent: {response}\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")
    agent.request_stop()
    if not agent_task.done():
        agent_task.cancel()


async def single_task(task: str):
    """Run agent on a single task."""
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "configs", "agent_config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    resolve_env_vars(config)
    config.setdefault("agent_config", {})["ui_enabled"] = False
    config.setdefault("perception_config", {})["sensors"] = []

    agent = Agent(config)
    await agent.setup_async()
    response_queue = queue.Queue()
    terminal_cfg = config.get("terminal_config") or {}
    response_timeout = float((config.get("llm_gateway_config") or {}).get("llm_timeout", 60.0))
    gateway = ResponseQueueGateway(terminal_cfg, agent.event_bus, response_queue, response_timeout=response_timeout)
    gateway.register_handlers()
    agent_task = asyncio.create_task(agent.run())

    print(f"Task: {task}")
    print("-" * 40)
    signal = gateway.build_input_signal(
        task,
        source=EventNames.PERCEPTION_TERMINAL,
        meta={"llm_stream": False},
    )
    trace_id = signal.trace_id
    await gateway.emit_input(
        signal,
        event_name=EventNames.PERCEPTION_STIMULI,
        await_response=False,
    )
    result = gateway.get_for_trace(trace_id, response_timeout)
    print(f"\n{result}")
    agent.request_stop()
    if not agent_task.done():
        agent_task.cancel()


def main():
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        asyncio.run(single_task(task))
    else:
        asyncio.run(interactive_mode())


if __name__ == "__main__":
    main()
