# model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class GitRepoTreeErrorCode:
    NOT_A_GIT_REPO = "NOT_A_GIT_REPO"
    GIT_COMMAND_FAILED = "GIT_COMMAND_FAILED"
    FILE_CREATION_FAILED = "FILE_CREATION_FAILED"
    FILE_READ_ERROR = "FILE_READ_ERROR"
    EMPTY_TREE = "EMPTY_TREE"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    SUCCESS = "SUCCESS"


class GitRepoTreeParams(BaseModel):
    git_repo_path: Optional[str] = Field(
        ".",
        description="Relative path to the Git repository. Defaults to the current directory."
    )


class GitRepoTreeResult(BaseModel):
    success: Optional[bool] = Field(None, description="Whether the tree creation was successful.")
    message: Optional[str] = Field(None, description="Status message or error description.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")