from typing import List, Dict, Any, Optional, Union
from aeiva.action.procedure import Procedure
from aeiva.action.task import Task

class Plan(Procedure):
    """
    Represents a plan, which is a structured roadmap for achieving a goal by executing tasks and sub-plans.
    Inherits common functionality from Procedure.
    """

    def __init__(self, name: str, steps: List[Union['Plan', Task]],
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
        self.type = "Plan"