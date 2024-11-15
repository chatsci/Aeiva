from typing import Optional, Dict
from pydantic import BaseModel


class ExecuteBashCommandParams(BaseModel):
    command: str
    session_id: Optional[str] = None
    restart: bool = False


class ExecuteBashCommandResult(BaseModel):
    output: Optional[Dict[str, Any]]
    error: Optional[str]
    error_code: str


class ExecuteBashCommandErrorCode:
    SUCCESS = "SUCCESS"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    INVALID_COMMAND = "INVALID_COMMAND"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"