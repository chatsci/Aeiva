# tools/analyze_gui/model.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class AnalyzeGuiErrorCode:
    UNSUPPORTED_PLATFORM = "UNSUPPORTED_PLATFORM"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    SUCCESS = "SUCCESS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"

class AnalyzeGuiParams(BaseModel):
    target_text: Optional[str] = Field(None, description="The text/name of the UI element to search for.")
    role: Optional[str] = Field(None, description="The role/type of the UI element to search for (e.g., 'button', 'textbox').")

class AnalyzeGuiResult(BaseModel):
    output: Optional[List[Dict[str, Any]]] = Field(None, description="List of matching GUI elements.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")