from typing import List
from pydantic import BaseModel, Field


class DownloadArxivPapersParams(BaseModel):
    query: str = Field(..., description="Search query for arXiv.")
    paper_ids: List[str] = Field(default_factory=list, description="Optional list of arXiv paper IDs.")
    max_results: int = Field(5, description="Maximum number of search results to download.")
    output_dir: str = Field("./", description="Directory to save downloaded PDFs.")


class DownloadArxivPapersResult(BaseModel):
    output: str = Field(..., description="Success message or details.")
    error: str = Field(None, description="Error message, if any.")
    error_code: str = Field(..., description="Error code.")


class DownloadArxivPapersErrorCode:
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"