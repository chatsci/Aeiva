# model.py

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class ExecuteJSScriptErrorCode:
    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    JS_EXECUTION_ERROR = "JS_EXECUTION_ERROR"
    WEBDRIVER_ERROR = "WEBDRIVER_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"


class ExecuteJSScriptParams(BaseModel):
    url: str = Field(..., description="The URL of the webpage to interact with.")
    script: str = Field(..., description="The JavaScript code to execute.")
    args: Optional[List[Any]] = Field(default=[], description="Optional arguments to pass to the script.")


class ExecuteJSScriptResult(BaseModel):
    result: Any = Field(None, description="The result of the script execution")