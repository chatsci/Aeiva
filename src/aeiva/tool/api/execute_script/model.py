# tools/execute_script/model.py

from pydantic import BaseModel, Field, confloat
from typing import Optional, List, Dict, Any

class ExecuteScriptErrorCode:
    UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
    SCRIPT_EXECUTION_FAILED = "SCRIPT_EXECUTION_FAILED"
    TIMEOUT_EXPIRED = "TIMEOUT_EXPIRED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    SUCCESS = "SUCCESS"

class ExecuteScriptParams(BaseModel):
    script_content: str = Field(..., description="The content of the script to execute.")
    language: Optional[str] = Field("python", description="The programming language of the script ('python', 'bash').")

class ExecuteScriptResult(BaseModel):
    output: Optional[str] = Field(None, description="The output or result of the script execution.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")