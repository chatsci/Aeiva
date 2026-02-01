"""
Task: A visualizable atomic unit for planning.

A Task represents a single unit of work that can be visualized
and organized into Plans, but cannot be directly executed.

Tasks are used for planning and visualization. When execution
is needed, a Plan (of Tasks) is converted to a Skill (of Actions).

Hierarchy:
    Step → Task (visualizable, for planning)
    Step → Action (executable, with Tool)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aeiva.action.step import Step, generate_step_id


@dataclass
class Task(Step):
    """
    A visualizable unit of work for planning.

    Tasks represent what needs to be done, not how to do it.
    They are composed into Plans and can be visualized to
    understand the work structure.

    When execution is needed:
        Plan (Tasks) → Skill (Actions) via ActionSystem

    Example:
        task = Task(
            name="fetch_weather",
            params={"city": "Seattle"},
            description="Get current weather for Seattle"
        )
    """

    def show(self) -> str:
        """
        Generate a human-readable representation.

        Returns:
            Formatted string showing task details
        """
        lines = [
            "─" * 40,
            f"Task: {self.name}",
            f"  ID: {self.id}",
            f"  Status: {self.status}",
        ]

        if self.description:
            lines.append(f"  Description: {self.description}")

        if self.params:
            lines.append("  Parameters:")
            for key, value in self.params.items():
                lines.append(f"    {key}: {value}")

        if self.dependent_ids:
            lines.append(f"  Dependencies: {', '.join(self.dependent_ids)}")

        lines.append("─" * 40)
        return "\n".join(lines)

    def __str__(self) -> str:
        return f"Task({self.name}, id={self.id}, status={self.status})"
