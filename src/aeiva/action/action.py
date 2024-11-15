from aeiva.action.step import Step
from aeiva.tool.tool import Tool
from aeiva.action.status import Status
from typing import List, Dict, Optional, Any

class Action(Step):
    """
    Represents an action that can be executed, extending from the Step class.
    An action is a tool with states and state management methods. It can execute functionality.
    """

    def __init__(self, name: str, params: Dict[str, Any] = None,
                 id: str = None, dependent_ids: Optional[List[str]] = None, 
                 type: Optional[str] = None, description: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, params=params,
                         id=id, dependent_ids=dependent_ids,
                         type=type, description=description,
                         metadata=metadata)
        self.type = "Action"
        self.tool = Tool(name)
        self.result = None

    def reset(self) -> None:
        """
        Resets the step status, making it ready for re-execution.
        """
        self.result = None
        self.status = Status.NOT_EXECUTED

    async def execute(self, params: Dict[str, Any]) -> Any:
        if self.tool is None:
            raise ValueError(f"Action {self.id} has no tool assigned for execution.")

        self.start()
        try:
            result = await self.tool.execute(params)  # Assuming the tool's execute method is async
            self.end(success=True)
            self.result = result
            return result
        except Exception as e:
            self.end(success=False)
            raise RuntimeError(f"Action {self.id} failed: {str(e)}")
