# model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class GitCloneErrorCode:
    MISSING_REPO_NAME = "MISSING_REPO_NAME"
    MISSING_COMMIT_ID = "MISSING_COMMIT_ID"
    NOT_A_GIT_REPO = "NOT_A_GIT_REPO"
    DESTINATION_EXISTS = "DESTINATION_EXISTS"
    MISSING_GITHUB_TOKEN = "MISSING_GITHUB_TOKEN"
    GIT_COMMAND_FAILED = "GIT_COMMAND_FAILED"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    SUCCESS = "SUCCESS"


class GitCloneParams(BaseModel):
    repo_name: str = Field(
        ...,
        description="The Git repository to clone in the format 'owner/repo'."
    )
    destination: Optional[str] = Field(
        None,
        description="The local directory to clone the repository into. Defaults to the current working directory."
    )
    just_reset: Optional[bool] = Field(
        False,
        description="If true, resets the existing repository to the specified commit."
    )
    commit_id: str = Field(
        "",
        description="The commit ID to reset to. Required if just_reset is true."
    )


class GitCloneResult(BaseModel):
    output: Optional[str] = Field(None, description="Command output if successful.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")