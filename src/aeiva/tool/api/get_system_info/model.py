# tools/get_system_info/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class GetSystemInfoErrorCode:
    GET_SYSTEM_INFO_FAILED = "GET_SYSTEM_INFO_FAILED"
    SUCCESS = "SUCCESS"

class GetSystemInfoParams(BaseModel):
    pass  # No parameters

class GetSystemInfoResult(BaseModel):
    output: Optional[Dict[str, Any]] = Field(None, description="System information data.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")