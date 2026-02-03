"""
Neuron Exception Hierarchy.

Provides specific exception types for neuron operations, enabling:
1. Precise error handling with narrow except clauses
2. Clear error categorization for monitoring
3. Rich context for debugging

Exception Hierarchy:
    NeuronError (base)
    ├── SignalError
    │   ├── SignalValidationError
    │   └── SignalRoutingError
    ├── ProcessingError
    │   ├── ProcessingTimeoutError
    │   └── ProcessingFailedError
    ├── StateError
    │   ├── StatePersistenceError
    │   └── StateLoadError
    └── CircuitBreakerOpen
"""

from typing import Any, Dict, Optional


class NeuronError(Exception):
    """Base exception for all neuron-related errors.

    Attributes:
        neuron_name: Name of the neuron where error occurred
        trace_id: Signal trace ID if available
        context: Additional context dictionary
    """

    def __init__(
        self,
        message: str,
        neuron_name: Optional[str] = None,
        trace_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.neuron_name = neuron_name
        self.trace_id = trace_id
        self.context = context or {}

        # Build rich message
        parts = [message]
        if neuron_name:
            parts.append(f"neuron={neuron_name}")
        if trace_id:
            parts.append(f"trace_id={trace_id}")

        super().__init__(" | ".join(parts))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for structured logging."""
        return {
            "error_type": self.__class__.__name__,
            "message": str(self.args[0]) if self.args else "",
            "neuron_name": self.neuron_name,
            "trace_id": self.trace_id,
            **self.context,
        }


# ═══════════════════════════════════════════════════════════════════
# SIGNAL ERRORS
# ═══════════════════════════════════════════════════════════════════

class SignalError(NeuronError):
    """Base class for signal-related errors."""
    pass


class SignalValidationError(SignalError):
    """Signal failed validation checks.

    Raised when:
    - Signal data doesn't match expected schema
    - Required fields are missing
    - Data types are incorrect
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        expected_type: Optional[type] = None,
        actual_type: Optional[type] = None,
        **kwargs,
    ):
        self.field = field
        self.expected_type = expected_type
        self.actual_type = actual_type

        context = kwargs.pop("context", {})
        if field:
            context["field"] = field
        if expected_type:
            context["expected_type"] = expected_type.__name__
        if actual_type:
            context["actual_type"] = actual_type.__name__

        super().__init__(message, context=context, **kwargs)


class SignalRoutingError(SignalError):
    """Signal could not be routed to destination.

    Raised when:
    - Target neuron doesn't exist
    - Queue is full and backpressure rejects signal
    - Hop count exceeded
    """

    def __init__(
        self,
        message: str,
        target: Optional[str] = None,
        reason: Optional[str] = None,
        **kwargs,
    ):
        self.target = target
        self.reason = reason

        context = kwargs.pop("context", {})
        if target:
            context["target"] = target
        if reason:
            context["reason"] = reason

        super().__init__(message, context=context, **kwargs)


# ═══════════════════════════════════════════════════════════════════
# PROCESSING ERRORS
# ═══════════════════════════════════════════════════════════════════

class ProcessingError(NeuronError):
    """Base class for processing-related errors."""
    pass


class ProcessingTimeoutError(ProcessingError):
    """Processing exceeded timeout limit.

    Raised when:
    - process() takes longer than config.process_timeout
    - External API call times out
    """

    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        elapsed_seconds: Optional[float] = None,
        **kwargs,
    ):
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds

        context = kwargs.pop("context", {})
        if timeout_seconds is not None:
            context["timeout_seconds"] = timeout_seconds
        if elapsed_seconds is not None:
            context["elapsed_seconds"] = elapsed_seconds

        super().__init__(message, context=context, **kwargs)


class ProcessingFailedError(ProcessingError):
    """Processing failed due to internal error.

    Wraps the original exception with neuron context.
    """

    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
        **kwargs,
    ):
        self.original_error = original_error

        context = kwargs.pop("context", {})
        if original_error:
            context["original_error_type"] = type(original_error).__name__
            context["original_error_message"] = str(original_error)

        super().__init__(message, context=context, **kwargs)


# ═══════════════════════════════════════════════════════════════════
# STATE ERRORS
# ═══════════════════════════════════════════════════════════════════

class StateError(NeuronError):
    """Base class for state-related errors."""
    pass


class StatePersistenceError(StateError):
    """Failed to persist state to storage.

    Raised when:
    - Storage backend is unavailable
    - Serialization fails
    - Write operation fails
    """
    pass


class StateLoadError(StateError):
    """Failed to load state from storage.

    Raised when:
    - State file is corrupted
    - Version mismatch requires migration
    - Deserialization fails
    """

    def __init__(
        self,
        message: str,
        stored_version: Optional[int] = None,
        expected_version: Optional[int] = None,
        **kwargs,
    ):
        self.stored_version = stored_version
        self.expected_version = expected_version

        context = kwargs.pop("context", {})
        if stored_version is not None:
            context["stored_version"] = stored_version
        if expected_version is not None:
            context["expected_version"] = expected_version

        super().__init__(message, context=context, **kwargs)


# ═══════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER
# ═══════════════════════════════════════════════════════════════════

class CircuitBreakerOpen(NeuronError):
    """Circuit breaker is open, rejecting requests.

    Raised when:
    - Too many consecutive errors occurred
    - Neuron is in degraded state
    - Manual circuit break was triggered
    """

    def __init__(
        self,
        message: str,
        consecutive_errors: Optional[int] = None,
        last_error: Optional[Exception] = None,
        **kwargs,
    ):
        self.consecutive_errors = consecutive_errors
        self.last_error = last_error

        context = kwargs.pop("context", {})
        if consecutive_errors is not None:
            context["consecutive_errors"] = consecutive_errors
        if last_error:
            context["last_error_type"] = type(last_error).__name__

        super().__init__(message, context=context, **kwargs)
