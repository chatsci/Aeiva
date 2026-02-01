"""
AEIVA Action Module

This module handles action execution using the neuron architecture.

Concepts:
    - Step: Atomic unit (Task or Action)
    - Procedure: Composite unit (Plan, Skill, or Experience)
    - Task: Visualizable step for planning
    - Action: Executable step with Tool
    - Plan: Composed of Tasks, visualizable
    - Skill: Composed of Actions, executable
    - Experience: Personalized Actions, needs validation

Main Components:
    - ActuatorNeuron: The primary action handler (neuron-based)
    - Skill: Executable composition of Actions
    - Plan: Visualizable composition of Tasks

Usage:
    from aeiva.action import ActuatorNeuron, Plan, Task, Skill, Action

    # Create a plan
    plan = Plan(
        name="my_plan",
        steps=[
            Task(name="step1", id="t1"),
            Task(name="step2", id="t2", dependent_ids=["t1"]),
        ]
    )

    # Execute via ActuatorNeuron
    neuron = ActuatorNeuron(config=action_config, event_bus=bus)
    await neuron.setup()
    result = await neuron.execute_plan(plan)

Deprecated:
    - ActionSystem: Use ActuatorNeuron instead
"""

from aeiva.action.status import Status
from aeiva.action.step import Step
from aeiva.action.procedure import Procedure
from aeiva.action.task import Task
from aeiva.action.action import Action
from aeiva.action.plan import Plan
from aeiva.action.skill import Skill
from aeiva.action.experience import Experience
from aeiva.action.actuator import ActuatorNeuron, ActuatorNeuronConfig

__all__ = [
    # Core types
    "Status",
    "Step",
    "Procedure",
    # Atomic units
    "Task",
    "Action",
    # Composite units
    "Plan",
    "Skill",
    "Experience",
    # Neuron
    "ActuatorNeuron",
    "ActuatorNeuronConfig",
]
