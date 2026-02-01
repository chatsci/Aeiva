"""
Config: Configuration dataclasses for neurons.

Configuration is separated from state to allow:
    - Clean dependency injection
    - Easy testing with different configs
    - YAML/JSON serialization for deployment
    - Inheritance for specialized neuron configs

Design Philosophy:
    - All configs have sensible defaults
    - Configs are immutable after creation
    - Specialized neurons extend NeuronConfig
"""

from dataclasses import dataclass
from enum import Enum


class BackpressureStrategy(Enum):
    """
    How to handle queue overflow when a neuron can't keep up.

    DROP_OLDEST: Remove the oldest signal to make room (good for real-time)
    DROP_NEWEST: Reject the incoming signal (good for preserving history)
    DROP_LOW_PRIORITY: Remove lowest priority signal (good for prioritized work)
    BLOCK: Wait until space is available (good for guaranteed delivery)
    """

    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    DROP_LOW_PRIORITY = "drop_low_priority"
    BLOCK = "block"


@dataclass
class NeuronConfig:
    """
    Base configuration for all neurons.

    This configuration controls timeouts, queue behavior, persistence,
    and error handling. Specialized neurons should subclass this.

    Timeouts:
        receive_timeout: Max wait time for incoming signals
        process_timeout: Max time allowed for processing a signal
        request_timeout: Max wait time for request-response pattern
        shutdown_timeout: Max time for graceful shutdown

    Queue Management:
        queue_size: Maximum signals that can be queued
        queue_high_watermark: Percentage at which to warn about backpressure
        backpressure_strategy: How to handle queue overflow

    Persistence:
        persist_identity: Whether to save IdentityState
        persist_learning: Whether to save LearningState
        persist_interval: Seconds between auto-saves

    Error Handling:
        max_consecutive_errors: Errors before circuit breaker trips
        error_retry_delay: Seconds to wait after an error
    """

    # Timeouts (seconds)
    receive_timeout: float = 30.0
    process_timeout: float = 10.0
    request_timeout: float = 10.0
    shutdown_timeout: float = 10.0

    # Queue management
    queue_size: int = 100
    queue_high_watermark: int = 80
    backpressure_strategy: BackpressureStrategy = BackpressureStrategy.DROP_OLDEST

    # Persistence
    persist_identity: bool = True
    persist_learning: bool = True
    persist_interval: float = 60.0

    # Error handling
    max_consecutive_errors: int = 5
    error_retry_delay: float = 1.0

    def with_overrides(self, **kwargs) -> "NeuronConfig":
        """
        Create a new config with some values overridden.

        Example:
            >>> base = NeuronConfig()
            >>> fast = base.with_overrides(process_timeout=1.0)
        """
        from dataclasses import asdict
        current = asdict(self)
        current.update(kwargs)
        return NeuronConfig(**current)
