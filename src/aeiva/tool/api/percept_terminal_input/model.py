# tools/percept_terminal_input/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class PerceptTerminalInputErrorCode:
    SESSION_TERMINATED = "SESSION_TERMINATED"
    INPUT_FAILED = "INPUT_FAILED"
    SUCCESS = "SUCCESS"

class PerceptTerminalInputParams(BaseModel):
    prompt_message: Optional[str] = Field("Please enter input: ", description="The prompt message to display to the user.")

class PerceptTerminalInputResult(BaseModel):
    output: Optional[str] = Field(None, description="The user input from the terminal.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")