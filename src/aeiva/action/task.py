from aeiva.action.step import Step
from aeiva.tool.tool import Tool
from typing import List, Dict, Optional, Any
from pprint import pprint

class Task(Step):
    """
    Represents the fundamental unit of work, extending from the Step class.
    Inherits shared attributes and methods from Step and adds task-specific functionality.
    """

    def __init__(self, name: str, params: Dict[str, Any] = None,
                 id: Optional[str] = None, dependent_ids: Optional[List[str]] = None, 
                 type: Optional[str] = None, description: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, params=params,
                         id=id, dependent_ids=dependent_ids,
                         type=type, description=description,
                         metadata=metadata)
        self.type = "Task"

    def show(self) -> None:
        print("---- Task Information ----")
        pprint(self.to_dict(), sort_dicts=False)
        print("---- End of Task ----")
