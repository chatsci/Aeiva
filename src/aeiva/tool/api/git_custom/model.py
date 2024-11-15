# model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class GitCustomErrorCode:
    MISSING_COMMAND = "MISSING_COMMAND"
    NOT_A_GIT_REPO = "NOT_A_GIT_REPO"
    GIT_COMMAND_FAILED = "GIT_COMMAND_FAILED"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    SUCCESS = "SUCCESS"


class GitCustomParams(BaseModel):
    cmd: str = Field(
        ...,
        description="The custom Git command to run. Do not include the 'git' prefix. Example: 'add -u', 'commit -m \"test-commit\"'."
    )
    cwd: Optional[str] = Field(
        None,
        description="The directory to run the Git command in. Defaults to the current working directory."
    )


class GitCustomResult(BaseModel):
    output: Optional[str] = Field(None, description="Command output if successful.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")