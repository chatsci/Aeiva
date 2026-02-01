"""
Plan: A visualizable composition of Tasks.

A Plan organizes Tasks into a dependency graph, representing
a roadmap for achieving a goal. Plans can be visualized but
not directly executed.

When execution is needed:
    Plan (Tasks) → Skill (Actions) via ActionSystem

Hierarchy:
    Procedure → Plan (composed of Tasks, visualizable)
    Procedure → Skill (composed of Actions, executable)
    Procedure → Experience (composed of Actions, needs validation)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from aeiva.action.procedure import Procedure, generate_procedure_id
from aeiva.action.task import Task


@dataclass
class Plan(Procedure):
    """
    A visualizable roadmap composed of Tasks.

    Plans represent what needs to be accomplished and in what order,
    organized as a directed acyclic graph of Tasks.

    Plans are for visualization and planning. For execution,
    convert to a Skill using ActionSystem.plan_to_skill().

    Example:
        # Create tasks
        task1 = Task(name="research", id="t1", description="Research topic")
        task2 = Task(name="outline", id="t2", dependent_ids=["t1"])
        task3 = Task(name="write", id="t3", dependent_ids=["t2"])

        # Create plan
        plan = Plan(
            name="write_article",
            steps=[task1, task2, task3],
            description="Write an article"
        )

        # Visualize
        print(plan.visualize_text())

        # Convert to skill for execution
        skill = action_system.plan_to_skill(plan)
        await skill.execute()
    """

    # Type hint for steps to indicate Tasks expected
    steps: List[Union["Plan", Task]] = field(default_factory=list)

    def add_task(self, task: Task) -> "Plan":
        """
        Add a task to the plan.

        Args:
            task: Task to add

        Returns:
            Self for chaining

        Raises:
            ValueError: If task has unresolved dependencies
        """
        # Verify dependencies exist
        existing_ids = {step.id for step in self.steps}
        for dep_id in task.dependent_ids:
            if dep_id not in existing_ids:
                raise ValueError(
                    f"Task '{task.id}' depends on '{dep_id}' which is not in the plan"
                )

        self.steps.append(task)
        self._build_graph()  # Rebuild graph with new task
        return self

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        step = self.get_step(task_id)
        return step if isinstance(step, Task) else None

    @property
    def tasks(self) -> List[Task]:
        """Get all tasks (excluding nested plans)."""
        return [step for step in self.steps if isinstance(step, Task)]

    @property
    def subplans(self) -> List["Plan"]:
        """Get all nested plans."""
        return [step for step in self.steps if isinstance(step, Plan)]

    def flatten(self) -> List[Task]:
        """
        Get all tasks including those in nested plans.

        Returns:
            Flat list of all tasks in topological order
        """
        all_tasks = []
        for step in self.topological_order():
            if isinstance(step, Task):
                all_tasks.append(step)
            elif isinstance(step, Plan):
                all_tasks.extend(step.flatten())
        return all_tasks

    def __str__(self) -> str:
        return f"Plan({self.name}, tasks={len(self.tasks)}, status={self.status})"
