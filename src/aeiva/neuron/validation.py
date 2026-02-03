"""
Signal Validation Framework.

Provides declarative validation for signal data, enabling neurons
to enforce contracts on their inputs.

Usage:
    class MyNeuron(BaseNeuron):
        SIGNAL_SCHEMA = {
            "text": {"type": str, "required": True},
            "metadata": {"type": dict, "required": False, "default": {}},
            "priority": {"type": int, "required": False, "validator": lambda x: 0 <= x <= 10},
        }

        async def process(self, signal: Signal) -> Any:
            # Data is guaranteed to match schema after validation
            data = self.validate_signal_data(signal)
            return self.do_work(data["text"])
"""

from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass

from .exceptions import SignalValidationError
from .signal import Signal


@dataclass
class FieldSpec:
    """Specification for a single field in signal data.

    Attributes:
        type: Expected type or tuple of types
        required: Whether field must be present
        default: Default value if not present (only for non-required)
        validator: Optional function that returns True if valid
        description: Human-readable description for error messages
    """
    type: Union[Type, tuple]
    required: bool = True
    default: Any = None
    validator: Optional[Callable[[Any], bool]] = None
    description: Optional[str] = None

    def validate(self, value: Any, field_name: str) -> Any:
        """Validate a value against this spec.

        Args:
            value: The value to validate
            field_name: Name of the field (for error messages)

        Returns:
            The validated value (possibly with default applied)

        Raises:
            SignalValidationError: If validation fails
        """
        # Type check
        if not isinstance(value, self.type):
            raise SignalValidationError(
                f"Field '{field_name}' has wrong type",
                field=field_name,
                expected_type=self.type if isinstance(self.type, type) else self.type[0],
                actual_type=type(value),
            )

        # Custom validator
        if self.validator is not None:
            try:
                if not self.validator(value):
                    raise SignalValidationError(
                        f"Field '{field_name}' failed validation",
                        field=field_name,
                        context={"description": self.description} if self.description else {},
                    )
            except SignalValidationError:
                raise
            except Exception as e:
                raise SignalValidationError(
                    f"Field '{field_name}' validator raised error: {e}",
                    field=field_name,
                )

        return value


def validate_signal_data(
    signal: Signal,
    schema: Dict[str, Union[FieldSpec, Dict[str, Any]]],
    neuron_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Validate signal data against a schema.

    Args:
        signal: The signal to validate
        schema: Dictionary mapping field names to FieldSpec or dict specs
        neuron_name: Name of neuron (for error context)

    Returns:
        Validated and normalized data dictionary

    Raises:
        SignalValidationError: If validation fails
    """
    data = signal.data

    # Handle non-dict data
    if not isinstance(data, dict):
        # If schema expects a single "data" field, wrap it
        if len(schema) == 1 and "data" in schema:
            data = {"data": data}
        else:
            raise SignalValidationError(
                "Signal data must be a dictionary",
                expected_type=dict,
                actual_type=type(signal.data),
                neuron_name=neuron_name,
                trace_id=signal.trace_id,
            )

    result = {}

    # Normalize schema entries to FieldSpec
    normalized_schema: Dict[str, FieldSpec] = {}
    for field_name, spec in schema.items():
        if isinstance(spec, FieldSpec):
            normalized_schema[field_name] = spec
        elif isinstance(spec, dict):
            normalized_schema[field_name] = FieldSpec(**spec)
        else:
            raise ValueError(f"Invalid schema spec for field '{field_name}'")

    # Validate each field
    for field_name, spec in normalized_schema.items():
        if field_name in data:
            result[field_name] = spec.validate(data[field_name], field_name)
        elif spec.required:
            raise SignalValidationError(
                f"Required field '{field_name}' is missing",
                field=field_name,
                neuron_name=neuron_name,
                trace_id=signal.trace_id,
            )
        else:
            result[field_name] = spec.default

    # Include extra fields not in schema (permissive by default)
    for field_name, value in data.items():
        if field_name not in result:
            result[field_name] = value

    return result


def require_type(
    value: Any,
    expected_type: Union[Type, tuple],
    field_name: str = "value",
    neuron_name: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> None:
    """Assert that a value has the expected type.

    Args:
        value: Value to check
        expected_type: Expected type or tuple of types
        field_name: Name for error message
        neuron_name: Neuron name for context
        trace_id: Signal trace ID for context

    Raises:
        SignalValidationError: If type doesn't match
    """
    if not isinstance(value, expected_type):
        raise SignalValidationError(
            f"{field_name} has wrong type",
            field=field_name,
            expected_type=expected_type if isinstance(expected_type, type) else expected_type[0],
            actual_type=type(value),
            neuron_name=neuron_name,
            trace_id=trace_id,
        )


def require_fields(
    data: Dict[str, Any],
    fields: List[str],
    neuron_name: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> None:
    """Assert that required fields are present.

    Args:
        data: Dictionary to check
        fields: List of required field names
        neuron_name: Neuron name for context
        trace_id: Signal trace ID for context

    Raises:
        SignalValidationError: If any field is missing
    """
    missing = [f for f in fields if f not in data]
    if missing:
        raise SignalValidationError(
            f"Missing required fields: {', '.join(missing)}",
            field=missing[0],
            neuron_name=neuron_name,
            trace_id=trace_id,
        )


# ═══════════════════════════════════════════════════════════════════
# COMMON VALIDATORS
# ═══════════════════════════════════════════════════════════════════

def non_empty_string(value: str) -> bool:
    """Validate that string is non-empty after stripping."""
    return isinstance(value, str) and len(value.strip()) > 0


def positive_number(value: Union[int, float]) -> bool:
    """Validate that number is positive."""
    return isinstance(value, (int, float)) and value > 0


def non_negative_number(value: Union[int, float]) -> bool:
    """Validate that number is non-negative."""
    return isinstance(value, (int, float)) and value >= 0


def in_range(min_val: float, max_val: float) -> Callable[[Union[int, float]], bool]:
    """Create validator for numeric range."""
    def validator(value: Union[int, float]) -> bool:
        return isinstance(value, (int, float)) and min_val <= value <= max_val
    return validator


def one_of(*allowed_values: Any) -> Callable[[Any], bool]:
    """Create validator for allowed values."""
    def validator(value: Any) -> bool:
        return value in allowed_values
    return validator


def list_of(item_type: Type) -> Callable[[list], bool]:
    """Create validator for list with specific item type."""
    def validator(value: list) -> bool:
        return isinstance(value, list) and all(isinstance(item, item_type) for item in value)
    return validator
