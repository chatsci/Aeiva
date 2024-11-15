# model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Tuple


class GitPatchErrorCode:
    NOT_A_GIT_REPO = "NOT_A_GIT_REPO"
    ADD_FILE_FAILED = "ADD_FILE_FAILED"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    STAGE_FAILED = "STAGE_FAILED"
    PATCH_GENERATION_FAILED = "PATCH_GENERATION_FAILED"
    NO_CHANGES = "NO_CHANGES"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    SUCCESS = "SUCCESS"


class GitPatchParams(BaseModel):
    new_file_paths: List[str] = Field(
        default=[],
        description="Paths of the files newly created to be included in the patch."
    )


class GitPatchResult(BaseModel):
    patch: Optional[str] = Field(None, description="The generated Git patch.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")