import networkx as nx
from typing import List, Dict, Any, Optional, Union

from aeiva.action.procedure import Procedure
from aeiva.action.action import Action


class Skill(Procedure):
    """
    Represents a skill, which is a structured roadmap for executing actions.
    Skills are composed of actions and can be executed.
    Inherits common functionality from Procedure.
    """

    def __init__(self, name: str, steps: List[Union['Skill', Action]],
                 id: Optional[str] = None, dependent_ids: Optional[List[str]] = None,
                 type: Optional[str] = None, description: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initializes a Skill by extending Procedure.
        """
        super().__init__(name=name, steps=steps,
                         id=id, dependent_ids=dependent_ids,
                         type=type, description=description,
                         metadata=metadata)
        self.type = "Skill"

    def get_topological_sort(self):
        """
        Returns the steps in topologically sorted order based on the dependency graph.
        Ensures that all prerequisite steps are executed before the dependent ones.
        """
        return list(nx.topological_sort(self.graph))

    async def execute(self):
        """
        Executes all actions in the skill based on the dependencies defined in the graph.
        This will run the actions asynchronously, respecting their dependencies.
        """
        self.start()

        # Perform topological sort right before execution
        sorted_steps = self.get_topological_sort()

        for step in sorted_steps:
            if isinstance(step, Action):
                print(f"Executing Action: {step.id} - {step.description}")
                await step.execute(step.params)  # Execute the action asynchronously
            elif isinstance(step, Skill):
                print(f"Executing Sub-Skill: {step.id}")
                await step.execute()  # If it's a sub-skill, execute the sub-skill

        self.end(success=self.is_successful)