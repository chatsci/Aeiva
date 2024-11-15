from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict


class CrawlParams(BaseModel):
    url: str = Field(..., description="The website URL to crawl.")


class CrawlResult(BaseModel):
    output: Optional[Dict[str, str]] = Field(
        None, description="Content of the crawled webpage."
    )
    error: Optional[str] = Field(None, description="Error message, if any.")
    error_code: Optional[str] = Field(None, description="Error code.")


class CrawlErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    INVALID_URL = "INVALID_URL"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    HTTP_ERROR = "HTTP_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"