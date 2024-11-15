# tools/play_music/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class PlayMusicErrorCode:
    MISSING_FILE_PATH = "MISSING_FILE_PATH"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PLAY_MUSIC_FAILED = "PLAY_MUSIC_FAILED"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    SUCCESS = "SUCCESS"

class PlayMusicParams(BaseModel):
    file_path: str = Field(..., description="The path to the music file.")
    loop: Optional[bool] = Field(False, description="Whether to loop the music continuously.")

class PlayMusicResult(BaseModel):
    output: Optional[str] = Field(None, description="A message indicating the result.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")