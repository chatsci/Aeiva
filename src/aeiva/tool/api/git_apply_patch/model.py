# model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class GitApplyPatchErrorCode:
    MISSING_PATCH = "MISSING_PATCH"
    NOT_A_GIT_REPO = "NOT_A_GIT_REPO"
    APPLY_PATCH_FAILED = "APPLY_PATCH_FAILED"
    LINT_ERRORS = "LINT_ERRORS"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    OS_ERROR = "OS_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    SUCCESS = "SUCCESS"


class GitApplyPatchParams(BaseModel):
    patch: str = Field(
        ...,
        description="The patch to apply in the format of a proper diff."
    )


class GitApplyPatchResult(BaseModel):
    message: Optional[str] = Field(None, description="Result message of applying the patch.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")