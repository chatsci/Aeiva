# tools/search_file_or_folder/model.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SearchFileOrFolderErrorCode:
    INVALID_SEARCH_TYPE = "INVALID_SEARCH_TYPE"
    SEARCH_FAILED = "SEARCH_FAILED"
    SUCCESS = "SUCCESS"

class SearchFileOrFolderParams(BaseModel):
    name: str = Field(..., description="The name of the file or folder to search for.")
    search_path: Optional[str] = Field(None, description="The path to start the search from.")
    search_type: Optional[str] = Field("both", description="Type of search - 'file', 'folder', or 'both'.")
    case_sensitive: Optional[bool] = Field(True, description="Whether the search is case-sensitive.")
    partial_match: Optional[bool] = Field(False, description="Whether to allow partial name matching.")

class SearchFileOrFolderResult(BaseModel):
    output: Optional[Dict[str, List[str]]] = Field(None, description="List of matched paths.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")