# toolkit/file_toolkit/move_file_or_folder/model.py

from enum import Enum
from pydantic import BaseModel, Field

class MoveFileOrFolderParams(BaseModel):
    source: str = Field(
        ..., 
        description="The path of the file or folder to move."
    )
    destination: str = Field(
        ..., 
        description="The target path where the file or folder will be moved."
    )

class MoveFileOrFolderResult(BaseModel):
    output: str = Field(
        ..., 
        description="Success message indicating the move operation was successful."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class MoveFileOrFolderErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    SHUTIL_ERROR = "SHUTIL_ERROR"
    FAILED_TO_MOVE = "FAILED_TO_MOVE"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"