# File: cognition/output_orchestrator/simple_output_orchestrator.py

import logging
from typing import Optional, Any

from aeiva.cognition.output_orchestrator.output_orchestrator import OutputOrchestrator
from aeiva.cognition.thought import Thought
from aeiva.action.plan import Plan
from aeiva.action.task import Task

logger = logging.getLogger(__name__)

class SimpleOutputOrchestrator(OutputOrchestrator):
    """
    Simple implementation that optionally converts thoughts into plans.
    """
    def __init__(self, config: Optional[Any] = None):
        self.config = config

    def setup(self) -> None:
        logger.debug("SimpleOutputOrchestrator setup complete.")

    def gate(self, thought: Thought) -> bool:
        """
        Decide whether to convert thought into a plan or pass through.
        """
        # For simplicity, check if the thought contains a command keyword
        #return 'execute' in thought.content.lower()  # TODO: sometime there is bug: thought.content is None.
        return False

    async def orchestrate(self, thought: Thought) -> Plan:
        """
        Convert thought into a plan.
        """
        # Simple implementation: create a plan based on the thought content
        task = Task(
            name='ExecuteCommand',
            params={'command': thought.content},
            id='task1',
            description='Execute the command from thought.'
        )
        plan = Plan(
            name='GeneratedPlan',
            steps=[task],
            id='plan1',
            description='Plan generated from thought.'
        )
        return plan
