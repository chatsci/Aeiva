from typing import List, Dict
from pydantic import BaseModel, Field


class SearchArxivPapersParams(BaseModel):
    query: str = Field(..., description="Search query for arXiv.")
    paper_ids: List[str] = Field(default_factory=list, description="Optional list of arXiv paper IDs.")
    max_results: int = Field(5, description="Maximum number of search results to return.")


class SearchArxivPapersResult(BaseModel):
    output: List[Dict[str, any]] = Field(..., description="List of paper details.")
    error: str = Field(None, description="Error message, if any.")
    error_code: str = Field(..., description="Error code.")


class SearchArxivPapersErrorCode:
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"