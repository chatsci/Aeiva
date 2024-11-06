#!/usr/bin/env python

from litellm.exceptions import (
    APIConnectionError,
    APIError,
    APIResponseValidationError,
    AuthenticationError,
    BadRequestError,
    BudgetExceededError,
    ContentPolicyViolationError,
    ContextWindowExceededError,
    InternalServerError,
    InvalidRequestError,
    JSONSchemaValidationError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    RejectedRequestError,
    ServiceUnavailableError,
    Timeout,
    UnprocessableEntityError,
    UnsupportedParamsError
)

class LLMGatewayError(Exception):
    """Unified exception class for all LLM-related errors."""

    def __init__(self, message: str, original_exception: Exception = None):
        super().__init__(message)
        self.original_exception = original_exception

# Mapping litellm exceptions to LLMGatewayError
LITELLM_EXCEPTION_MAP = {
    APIConnectionError: LLMGatewayError,
    APIError: LLMGatewayError,
    APIResponseValidationError: LLMGatewayError,
    AuthenticationError: LLMGatewayError,
    BadRequestError: LLMGatewayError,
    BudgetExceededError: LLMGatewayError,
    ContentPolicyViolationError: LLMGatewayError,
    ContextWindowExceededError: LLMGatewayError,
    InternalServerError: LLMGatewayError,
    InvalidRequestError: LLMGatewayError,
    JSONSchemaValidationError: LLMGatewayError,
    NotFoundError: LLMGatewayError,
    PermissionDeniedError: LLMGatewayError,
    RateLimitError: LLMGatewayError,
    RejectedRequestError: LLMGatewayError,
    ServiceUnavailableError: LLMGatewayError,
    Timeout: LLMGatewayError,
    UnprocessableEntityError: LLMGatewayError,
    UnsupportedParamsError: LLMGatewayError
}

def llm_gateway_exception(e: Exception) -> LLMGatewayError:
    """Converts a litellm exception to a unified LLMGatewayError."""
    exception_type = type(e)
    mapped_exception = LITELLM_EXCEPTION_MAP.get(exception_type, LLMGatewayError)
    return mapped_exception(str(e), original_exception=e)