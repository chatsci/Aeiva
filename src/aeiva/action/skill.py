"""
Skill: An executable composition of Actions.

A Skill organizes Actions into a dependency graph and can
execute them in the correct order. Skills are the executable
counterpart to Plans.

Conversion:
    Plan (Tasks) → Skill (Actions) via ActionSystem

Hierarchy:
    Procedure → Plan (composed of Tasks, visualizable)
    Procedure → Skill (composed of Actions, executable)
    Procedure → Experience (composed of Actions, needs validation)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable
import asyncio
import logging

from aeiva.action.procedure import Procedure, generate_procedure_id
from aeiva.action.action import Action
from aeiva.action.status import Status

logger = logging.getLogger(__name__)


@dataclass
class Skill(Procedure):
    """
    An executable composition of Actions.

    Skills organize Actions in a dependency graph and execute them
    in topological order, respecting dependencies.

    Execution Features:
        - Dependency-aware execution ordering
        - Parallel execution of independent actions (optional)
        - Progress tracking
        - Error handling with rollback support

    Example:
        # Create actions
        action1 = Action(name="fetch_data", id="a1")
        action2 = Action(name="process", id="a2", dependent_ids=["a1"])
        action3 = Action(name="save", id="a3", dependent_ids=["a2"])

        # Create skill
        skill = Skill(
            name="data_pipeline",
            steps=[action1, action2, action3],
            description="Fetch, process, and save data"
        )

        # Execute
        await skill.execute()

    Attributes:
        steps: List of Actions or nested Skills
        parallel: Whether to execute independent actions in parallel
    """

    steps: List[Union["Skill", Action]] = field(default_factory=list)
    parallel: bool = field(default=False)

    async def execute(
        self,
        on_action_complete: Optional[Callable[[Action], Awaitable[None]]] = None,
        on_action_error: Optional[Callable[[Action, Exception], Awaitable[None]]] = None
    ) -> bool:
        """
        Execute all actions in dependency order.

        Args:
            on_action_complete: Optional callback when an action completes
            on_action_error: Optional callback when an action fails

        Returns:
            True if all actions succeeded, False otherwise

        Raises:
            RuntimeError: If execution fails and no error handler provided
        """
        self.start()
        logger.info(f"Executing skill '{self.name}' ({self.id})")

        try:
            if self.parallel:
                success = await self._execute_parallel(on_action_complete, on_action_error)
            else:
                success = await self._execute_sequential(on_action_complete, on_action_error)

            if success:
                self.succeed()
                logger.info(f"Skill '{self.name}' completed successfully")
            else:
                self.fail()
                logger.warning(f"Skill '{self.name}' completed with failures")

            return success

        except Exception as e:
            self.fail()
            logger.error(f"Skill '{self.name}' failed: {e}")
            raise

    async def _execute_sequential(
        self,
        on_complete: Optional[Callable[[Action], Awaitable[None]]] = None,
        on_error: Optional[Callable[[Action, Exception], Awaitable[None]]] = None
    ) -> bool:
        """Execute actions sequentially in topological order."""
        all_success = True

        for step in self.topological_order():
            try:
                if isinstance(step, Action):
                    logger.debug(f"Executing action: {step.name} ({step.id})")
                    await step.execute()

                    if on_complete:
                        await on_complete(step)

                elif isinstance(step, Skill):
                    logger.debug(f"Executing sub-skill: {step.name} ({step.id})")
                    success = await step.execute(on_complete, on_error)
                    if not success:
                        all_success = False

            except Exception as e:
                all_success = False
                if on_error:
                    await on_error(step, e)
                else:
                    raise

        return all_success

    async def _execute_parallel(
        self,
        on_complete: Optional[Callable[[Action], Awaitable[None]]] = None,
        on_error: Optional[Callable[[Action, Exception], Awaitable[None]]] = None
    ) -> bool:
        """
        Execute independent actions in parallel.

        Groups actions by dependency level and executes each level
        in parallel while respecting dependencies between levels.
        """
        all_success = True

        while True:
            # Get actions that are ready to execute
            ready = self.ready_steps()

            if not ready:
                # No more ready actions
                break

            # Execute all ready actions in parallel
            async def execute_step(step):
                try:
                    if isinstance(step, Action):
                        await step.execute()
                        if on_complete:
                            await on_complete(step)
                    elif isinstance(step, Skill):
                        await step.execute(on_complete, on_error)
                except Exception as e:
                    if on_error:
                        await on_error(step, e)
                    raise

            try:
                await asyncio.gather(*[execute_step(step) for step in ready])
            except Exception:
                all_success = False
                # Continue to try remaining actions

        return all_success and self.is_successful

    def add_action(self, action: Action) -> "Skill":
        """
        Add an action to the skill.

        Args:
            action: Action to add

        Returns:
            Self for chaining
        """
        existing_ids = {step.id for step in self.steps}
        for dep_id in action.dependent_ids:
            if dep_id not in existing_ids:
                raise ValueError(
                    f"Action '{action.id}' depends on '{dep_id}' which is not in the skill"
                )

        self.steps.append(action)
        self._build_graph()
        return self

    def get_action(self, action_id: str) -> Optional[Action]:
        """Get an action by ID."""
        step = self.get_step(action_id)
        return step if isinstance(step, Action) else None

    @property
    def actions(self) -> List[Action]:
        """Get all actions (excluding nested skills)."""
        return [step for step in self.steps if isinstance(step, Action)]

    @property
    def subskills(self) -> List["Skill"]:
        """Get all nested skills."""
        return [step for step in self.steps if isinstance(step, Skill)]

    def __str__(self) -> str:
        return f"Skill({self.name}, actions={len(self.actions)}, status={self.status})"
