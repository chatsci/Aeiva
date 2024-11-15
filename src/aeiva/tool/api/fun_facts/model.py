# tools/fun_facts/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class FunFactsErrorCode:
    MISSING_API_KEY = "MISSING_API_KEY"
    FETCH_FAILED = "FETCH_FAILED"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    SUCCESS = "SUCCESS"

class FunFactsParams(BaseModel):
    rapidapi_key: Optional[str] = Field(None, description="The RapidAPI key. If not provided, it will use the key from the environment variables.")

class FunFactsResult(BaseModel):
    output: Optional[Dict[str, Any]] = Field(None, description="The fetched fun facts data.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")