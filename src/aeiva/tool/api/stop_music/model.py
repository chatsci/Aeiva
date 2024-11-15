# tools/stop_music/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class StopMusicErrorCode:
    STOP_MUSIC_FAILED = "STOP_MUSIC_FAILED"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    SUCCESS = "SUCCESS"

class StopMusicParams(BaseModel):
    pass  # No parameters

class StopMusicResult(BaseModel):
    output: Optional[str] = Field(None, description="A message indicating the result.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")