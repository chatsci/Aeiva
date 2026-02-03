"""
BaseNeuron: The foundational implementation of a Code Neuron.

A neuron is the atomic unit of computation in AEIVA. Like biological
neurons that receive dendrite signals, process in the soma, and send
via axons, code neurons follow the pattern:

    receive() → process() → send()

This module provides BaseNeuron, a ready-to-use implementation that
handles all the infrastructure concerns:
    - Event subscription and signal routing
    - Backpressure and queue management
    - Request-response pattern
    - State persistence
    - Health monitoring
    - Graceful shutdown
    - Input validation
    - Circuit breaker pattern

Subclasses only need to override process() to implement their logic.

Example:
    >>> from aeiva.event import EventBus
    >>>
    >>> class EchoNeuron(BaseNeuron):
    ...     async def process(self, signal):
    ...         return f"Echo: {signal.data}"
    >>>
    >>> bus = EventBus()
    >>> neuron = EchoNeuron(name="echo", event_bus=bus)

Design Philosophy:
    - Composition over inheritance
    - Sensible defaults, everything configurable
    - Async-first for real-world performance
    - Observable by default
    - Fail-fast with clear errors
"""

from typing import Any, Callable, Dict, List, Optional, Type, Union, TYPE_CHECKING
from asyncio import Queue
from dataclasses import asdict, fields
from uuid import uuid4
from datetime import timezone
from enum import Enum
import asyncio
import logging
import time

from .signal import Signal
from .state import IdentityState, WorkingState, LearningState
from .config import NeuronConfig, BackpressureStrategy
from .metrics import NeuronMetrics
from .exceptions import (
    NeuronError,
    SignalValidationError,
    SignalRoutingError,
    ProcessingError,
    ProcessingTimeoutError,
    ProcessingFailedError,
    StatePersistenceError,
    StateLoadError,
    CircuitBreakerOpen,
)
from .validation import validate_signal_data, FieldSpec

if TYPE_CHECKING:
    from aeiva.event import EventBus, Event

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels for neurons."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"
    CIRCUIT_OPEN = "circuit_open"


class BaseNeuron:
    """
    Base implementation for all neurons.

    Structure:
        ├── State: identity, working, learning
        ├── Lifecycle: setup, teardown, graceful_shutdown
        ├── Core: receive, process, send
        ├── Validation: validate_signal, SIGNAL_SCHEMA
        ├── Request-Response: request
        ├── Persistence: save_state, load_state
        ├── Circuit Breaker: _check_circuit, _reset_circuit
        └── Execution: run_once, run_forever

    Class Attributes (override in subclasses):
        SUBSCRIPTIONS: Event patterns to subscribe to
        EMISSIONS: Event patterns this neuron emits (documentation)
        CONFIG_CLASS: Configuration class to use
        STATE_VERSION: For state migration on schema changes
        SIGNAL_SCHEMA: Optional schema for input validation
    """

    # Override in subclasses
    SUBSCRIPTIONS: List[str] = []
    EMISSIONS: List[str] = []
    CONFIG_CLASS: Type[NeuronConfig] = NeuronConfig
    STATE_VERSION: int = 1
    SIGNAL_SCHEMA: Optional[Dict[str, Union[FieldSpec, Dict[str, Any]]]] = None

    def __init__(
        self,
        name: str = None,
        config: NeuronConfig = None,
        event_bus: Any = None,
        storage: Any = None,
    ):
        """
        Initialize a neuron.

        Args:
            name: Unique identifier (defaults to class name lowercase)
            config: Configuration object
            event_bus: Event bus for pub/sub (uses global if not provided)
            storage: Storage backend for persistence (optional)
        """
        self.name = name or self.__class__.__name__.lower()
        self.config = config or self.CONFIG_CLASS()
        self.events = event_bus
        self.storage = storage

        # Three-layer state
        self.identity = IdentityState()
        self.working = WorkingState()
        self.learning = LearningState()

        # Metrics
        self.metrics = NeuronMetrics(self.name)

        # Runtime state
        self.input_queue: Optional[Queue] = None
        self.running = False
        self.accepting = True
        self.subscribed_callbacks: List[Callable] = []

        # Circuit breaker state
        self._consecutive_errors = 0
        self._circuit_open = False
        self._circuit_opened_at: Optional[float] = None
        self._last_error: Optional[Exception] = None

    @classmethod
    def build_config(cls, config: Any) -> NeuronConfig:
        """
        Build a CONFIG_CLASS instance from a dict or config object.

        This normalizes configuration handling across neurons and
        ignores unknown keys (e.g., 'enabled').
        """
        if isinstance(config, cls.CONFIG_CLASS):
            return config
        if not isinstance(config, dict):
            return cls.CONFIG_CLASS()
        allowed = {f.name for f in fields(cls.CONFIG_CLASS)}
        filtered = {k: v for k, v in config.items() if k in allowed}
        return cls.CONFIG_CLASS(**filtered)

    # ═══════════════════════════════════════════════════════════════════
    # STRUCTURED LOGGING HELPERS
    # ═══════════════════════════════════════════════════════════════════

    def _log(
        self,
        level: int,
        message: str,
        trace_id: Optional[str] = None,
        **extra,
    ) -> None:
        """Log with structured context.

        Args:
            level: Logging level (e.g., logging.INFO)
            message: Log message
            trace_id: Optional trace ID for correlation
            **extra: Additional structured fields
        """
        context = {"neuron": self.name}
        if trace_id:
            context["trace_id"] = trace_id
        context.update(extra)

        # Format as structured log
        context_str = " ".join(f"{k}={v}" for k, v in context.items())
        logger.log(level, f"{message} | {context_str}")

    def _log_info(self, message: str, trace_id: Optional[str] = None, **extra) -> None:
        """Log info with context."""
        self._log(logging.INFO, message, trace_id, **extra)

    def _log_warning(self, message: str, trace_id: Optional[str] = None, **extra) -> None:
        """Log warning with context."""
        self._log(logging.WARNING, message, trace_id, **extra)

    def _log_error(self, message: str, trace_id: Optional[str] = None, **extra) -> None:
        """Log error with context."""
        self._log(logging.ERROR, message, trace_id, **extra)

    def _log_debug(self, message: str, trace_id: Optional[str] = None, **extra) -> None:
        """Log debug with context."""
        self._log(logging.DEBUG, message, trace_id, **extra)

    # ═══════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════

    async def setup(self) -> None:
        """
        Initialize the neuron before running.

        This method:
            1. Restores state from storage (if available)
            2. Creates the input queue
            3. Subscribes to events via callbacks

        Override to add custom initialization, but call super().setup().

        Raises:
            StateLoadError: If state restoration fails
        """
        # Restore persisted state
        if self.storage:
            try:
                await self.load_state()
            except StateLoadError:
                self._log_warning("Failed to load state, starting fresh")

        # Create input queue
        self.input_queue = Queue(maxsize=self.config.queue_size)

        # Subscribe to events using callback pattern
        if self.events:
            patterns = self.SUBSCRIPTIONS or [f"{self.name}.*"]
            for pattern in patterns:
                callback = self.create_event_callback(pattern)
                self.events.subscribe(pattern, callback)
                self.subscribed_callbacks.append(callback)

            self._log_info("Subscribed to events", patterns=patterns)

        self._log_info("Setup complete")

    def create_event_callback(self, pattern: str) -> Callable:
        """
        Create a callback function for EventBus subscription.

        The callback converts Event objects to Signal objects and
        enqueues them for processing.

        Args:
            pattern: The event pattern this callback handles

        Returns:
            An async callback function compatible with EventBus
        """
        async def on_event(event: "Event") -> None:
            if not self.accepting:
                return

            # Convert Event to Signal
            signal = self.event_to_signal(event)

            # Enqueue for processing
            await self.enqueue(signal)

        # Name the callback for EventBus logging
        on_event.__name__ = f"{self.name}_on_{pattern.replace('*', 'any').replace('.', '_')}"
        return on_event

    def event_to_signal(self, event: "Event") -> Signal:
        """
        Convert an EventBus Event to a Neuron Signal.

        This bridges the existing event system with the neuron architecture.
        If the event payload is already a Signal, it's returned as-is.
        Otherwise, a new Signal is created wrapping the payload.

        Args:
            event: The Event from EventBus

        Returns:
            A Signal for neuron processing
        """
        # If payload is already a Signal (from another neuron), use it
        if isinstance(event.payload, Signal):
            return event.payload

        # Otherwise, wrap the payload in a new Signal
        ts = None
        if event.timestamp:
            if event.timestamp.tzinfo is None:
                ts = event.timestamp.replace(tzinfo=timezone.utc).timestamp()
            else:
                ts = event.timestamp.timestamp()
        return Signal(
            source=event.name,
            data=event.payload,
            timestamp=ts if ts is not None else time.time(),
            priority=event.priority,
        )

    def signal_to_event_args(self, event_name: str, signal: Signal) -> dict:
        """
        Convert a Signal to arguments for EventBus.emit().

        Args:
            event_name: The event name to emit
            signal: The Signal to convert

        Returns:
            Dictionary of arguments for EventBus.emit()
        """
        return {
            "event_name": event_name,
            "payload": signal,  # Pass Signal as payload for other neurons
            "priority": signal.priority,
        }

    async def teardown(self) -> None:
        """
        Clean up resources when stopping.

        This method unsubscribes callbacks and releases resources.
        Override to add custom cleanup, but call super().teardown().
        """
        # Unsubscribe all callbacks
        if self.events:
            for callback in self.subscribed_callbacks:
                self.events.unsubscribe(callback)
        self.subscribed_callbacks.clear()

        self._log_info("Teardown complete")

    async def graceful_shutdown(self, timeout: float = None) -> None:
        """
        Gracefully stop the neuron.

        This method:
            1. Stops accepting new signals
            2. Waits for pending requests to complete
            3. Drains remaining signals from the queue
            4. Saves state
            5. Tears down

        Args:
            timeout: Maximum time to wait (defaults to config)
        """
        timeout = timeout or self.config.shutdown_timeout
        self._log_info("Shutting down gracefully", timeout=timeout)

        # Stop accepting new signals
        self.accepting = False

        # Wait for pending requests (1/3 of timeout)
        if self.working.pending_requests:
            pending = list(self.working.pending_requests.values())
            try:
                await asyncio.wait(pending, timeout=timeout / 3)
            except asyncio.TimeoutError:
                self._log_warning("Timeout waiting for pending requests")

        # Drain queue (1/3 of timeout)
        deadline = time.time() + timeout / 3
        drained = 0
        while self.input_queue and not self.input_queue.empty():
            if time.time() >= deadline:
                self._log_warning("Timeout draining queue", remaining=self.input_queue.qsize())
                break
            try:
                signal = self.input_queue.get_nowait()
                remaining = deadline - time.time()
                await asyncio.wait_for(
                    self.process(signal),
                    timeout=max(0.1, remaining)
                )
                drained += 1
            except asyncio.TimeoutError:
                break
            except asyncio.QueueEmpty:
                break
            except Exception as e:
                self._log_warning("Error draining signal", error=str(e))

        if drained > 0:
            self._log_info("Drained signals from queue", count=drained)

        # Save state
        if self.storage:
            try:
                await self.save_state()
            except StatePersistenceError as e:
                self._log_error("Failed to save state", error=str(e))

        # Stop running
        self.running = False
        await self.teardown()

        self._log_info("Shutdown complete")

    # ═══════════════════════════════════════════════════════════════════
    # VALIDATION
    # ═══════════════════════════════════════════════════════════════════

    def validate_signal(self, signal: Signal) -> Dict[str, Any]:
        """
        Validate signal data against SIGNAL_SCHEMA.

        Override SIGNAL_SCHEMA in subclasses to define expected data format.
        If no schema is defined, returns signal.data unchanged.

        Args:
            signal: The signal to validate

        Returns:
            Validated and normalized data dictionary

        Raises:
            SignalValidationError: If validation fails
        """
        if self.SIGNAL_SCHEMA is None:
            # No schema defined, pass through
            if isinstance(signal.data, dict):
                return signal.data
            return {"data": signal.data}

        return validate_signal_data(
            signal,
            self.SIGNAL_SCHEMA,
            neuron_name=self.name,
        )

    # ═══════════════════════════════════════════════════════════════════
    # CIRCUIT BREAKER
    # ═══════════════════════════════════════════════════════════════════

    def _check_circuit(self, signal: Optional[Signal] = None) -> None:
        """
        Check if circuit breaker allows processing.

        Args:
            signal: Optional signal for context in error

        Raises:
            CircuitBreakerOpen: If circuit is open
        """
        if not self._circuit_open:
            return

        # Check if recovery period has passed
        recovery_time = self.config.error_retry_delay * 10  # 10x retry delay
        if self._circuit_opened_at and time.time() - self._circuit_opened_at > recovery_time:
            self._log_info("Circuit breaker attempting recovery")
            self._circuit_open = False
            self._circuit_opened_at = None
            return

        raise CircuitBreakerOpen(
            "Circuit breaker is open",
            neuron_name=self.name,
            trace_id=signal.trace_id if signal else None,
            consecutive_errors=self._consecutive_errors,
            last_error=self._last_error,
        )

    def _record_success(self) -> None:
        """Record a successful processing, resetting circuit breaker."""
        self._consecutive_errors = 0
        self._last_error = None
        if self._circuit_open:
            self._log_info("Circuit breaker recovered")
            self._circuit_open = False
            self._circuit_opened_at = None

    def _record_error(self, error: Exception, signal: Optional[Signal] = None) -> None:
        """
        Record a processing error, potentially opening circuit.

        Args:
            error: The error that occurred
            signal: Optional signal for context
        """
        self._consecutive_errors += 1
        self._last_error = error
        self.metrics.record_error(error)

        trace_id = signal.trace_id if signal else None
        self._log_error(
            "Processing error",
            trace_id=trace_id,
            error_type=type(error).__name__,
            error_message=str(error),
            consecutive_errors=self._consecutive_errors,
        )

        if self._consecutive_errors >= self.config.max_consecutive_errors:
            self._circuit_open = True
            self._circuit_opened_at = time.time()
            self._log_error(
                "Circuit breaker opened",
                trace_id=trace_id,
                threshold=self.config.max_consecutive_errors,
            )

    # ═══════════════════════════════════════════════════════════════════
    # CORE: receive → process → send
    # ═══════════════════════════════════════════════════════════════════

    async def receive(self) -> Optional[Signal]:
        """
        Receive the next signal from the input queue.

        Returns None if:
            - Timeout occurs
            - Signal is a response (handled internally)

        Returns:
            The next signal to process, or None
        """
        try:
            signal = await asyncio.wait_for(
                self.input_queue.get(),
                timeout=self.config.receive_timeout
            )
            self.working.current_input = signal

            # Handle response signals internally
            if ".response" in getattr(signal, "source", ""):
                await self.handle_response(signal)
                return None

            return signal

        except asyncio.TimeoutError:
            return None

    async def process(self, signal: Signal) -> Any:
        """
        Process a signal and produce output.

        This is the method subclasses should override to implement
        their specific logic. The default implementation simply
        returns the signal's data.

        Args:
            signal: The signal to process

        Returns:
            Output to be sent downstream (or None to skip sending)
        """
        return signal.data

    async def send(self, output: Any, parent: Signal = None) -> None:
        """
        Send output to downstream neurons via EventBus.

        Args:
            output: The data to send (None skips sending)
            parent: The signal that triggered this output (for tracing)

        Raises:
            SignalRoutingError: If emit fails
        """
        if output is None:
            return

        if parent:
            signal = parent.child(self.name, output)
        else:
            signal = Signal(source=self.name, data=output)

        self.working.last_output = output

        if self.events:
            event_name = f"{self.name}.output"
            emit_args = self.signal_to_event_args(event_name, signal)
            success = await self.events.emit(**emit_args)
            if not success:
                raise SignalRoutingError(
                    "Failed to emit signal (hop count exceeded)",
                    neuron_name=self.name,
                    trace_id=signal.trace_id,
                    target=event_name,
                    reason="hop_count_exceeded",
                )

    # ═══════════════════════════════════════════════════════════════════
    # REQUEST-RESPONSE
    # ═══════════════════════════════════════════════════════════════════

    async def request(
        self,
        target: str,
        data: Any,
        timeout: float = None
    ) -> Any:
        """
        Send a request and wait for a response.

        This implements synchronous semantics over the async event system.
        Use when you need a result from another neuron.

        Args:
            target: Name of the neuron to request from
            data: Request payload
            timeout: Max wait time (defaults to config)

        Returns:
            The response data

        Raises:
            ProcessingTimeoutError: If no response within timeout

        Example:
            >>> memories = await self.request("memory", {"query": "recent"})
        """
        timeout = timeout or self.config.request_timeout
        request_id = uuid4().hex[:8]

        # Create future to wait on
        future: asyncio.Future = asyncio.Future()
        self.working.pending_requests[request_id] = future

        # Send request
        if self.events:
            request_signal = Signal(
                source=self.name,
                data={
                    "payload": data,
                    "request_id": request_id,
                    "reply_to": self.name,
                }
            )
            event_name = f"{target}.request"
            emit_args = self.signal_to_event_args(event_name, request_signal)
            await self.events.emit(**emit_args)

        # Wait for response
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            raise ProcessingTimeoutError(
                f"Request to {target} timed out",
                neuron_name=self.name,
                timeout_seconds=timeout,
                context={"target": target, "request_id": request_id},
            )
        finally:
            self.working.pending_requests.pop(request_id, None)

    async def handle_response(self, signal: Signal) -> None:
        """
        Handle an incoming response signal.

        This completes the future created by a previous request().
        """
        data = signal.data
        if not isinstance(data, dict):
            return

        request_id = data.get("request_id")
        if request_id and request_id in self.working.pending_requests:
            future = self.working.pending_requests[request_id]
            if not future.done():
                future.set_result(data.get("result"))

    async def respond(
        self,
        signal: Signal,
        result: Any
    ) -> None:
        """
        Send a response to a request.

        Use this in process() when handling request signals.

        Args:
            signal: The request signal
            result: The result to send back
        """
        data = signal.data
        if not isinstance(data, dict):
            return

        request_id = data.get("request_id")
        reply_to = data.get("reply_to")

        if request_id and reply_to and self.events:
            response_signal = Signal(
                source=self.name,
                data={
                    "request_id": request_id,
                    "result": result,
                }
            )
            event_name = f"{reply_to}.response"
            emit_args = self.signal_to_event_args(event_name, response_signal)
            await self.events.emit(**emit_args)

    # ═══════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════

    async def save_state(self) -> None:
        """
        Persist state to storage.

        Saves identity and learning state based on config.
        Working state is never persisted (it's ephemeral).

        Raises:
            StatePersistenceError: If save fails
        """
        if not self.storage:
            return

        state = {
            "name": self.name,
            "version": self.STATE_VERSION,
            "timestamp": time.time(),
        }

        if self.config.persist_identity:
            state["identity"] = asdict(self.identity)

        if self.config.persist_learning:
            state["learning"] = asdict(self.learning)

        try:
            await self.storage.save(f"neuron:{self.name}", state)
            self._log_debug("State saved")
        except Exception as e:
            raise StatePersistenceError(
                f"Failed to save state: {e}",
                neuron_name=self.name,
            ) from e

    async def load_state(self) -> bool:
        """
        Restore state from storage.

        Returns:
            True if state was restored, False if no state found

        Raises:
            StateLoadError: If state exists but cannot be loaded
        """
        if not self.storage:
            return False

        try:
            state = await self.storage.load(f"neuron:{self.name}")
        except Exception as e:
            raise StateLoadError(
                f"Failed to load state: {e}",
                neuron_name=self.name,
            ) from e

        if state is None:
            return False

        # Version check
        stored_version = state.get("version", 1)
        if stored_version != self.STATE_VERSION:
            raise StateLoadError(
                "State version mismatch",
                neuron_name=self.name,
                stored_version=stored_version,
                expected_version=self.STATE_VERSION,
            )

        if "identity" in state:
            self.identity = IdentityState(**state["identity"])

        if "learning" in state:
            self.learning = LearningState(**state["learning"])

        self._log_info("State restored", version=stored_version)
        return True

    # ═══════════════════════════════════════════════════════════════════
    # EXECUTION
    # ═══════════════════════════════════════════════════════════════════

    async def run_once(self, signal: Signal = None) -> Any:
        """
        Run a single receive-process-send cycle.

        Useful for testing and controlled execution.

        Args:
            signal: Signal to process (if None, receives from queue)

        Returns:
            The output of process()

        Raises:
            CircuitBreakerOpen: If circuit breaker is open
            SignalValidationError: If signal fails validation
            ProcessingError: If processing fails
        """
        if signal is None:
            signal = await self.receive()
            if signal is None:
                return None

        # Check circuit breaker
        self._check_circuit(signal)

        # Validate if schema defined
        if self.SIGNAL_SCHEMA:
            self.validate_signal(signal)

        output = await self.process(signal)
        await self.send(output, parent=signal)
        return output

    async def run_forever(self) -> None:
        """
        Run the neuron's main loop until stopped.

        This is the primary execution method. It:
            1. Calls setup()
            2. Loops: receive → process → send
            3. Handles errors with circuit breaker
            4. Calls teardown() when stopped

        The loop handles these exception types specifically:
            - asyncio.CancelledError: Propagated for clean shutdown
            - CircuitBreakerOpen: Waits for recovery
            - SignalValidationError: Logged, signal skipped
            - ProcessingTimeoutError: Logged, signal skipped
            - NeuronError: Logged with context
            - Exception: Logged, triggers circuit breaker
        """
        await self.setup()
        self.running = True

        try:
            while self.running:
                try:
                    # Check circuit breaker before receiving
                    try:
                        self._check_circuit()
                    except CircuitBreakerOpen:
                        await asyncio.sleep(self.config.error_retry_delay)
                        continue

                    # Receive
                    signal = await self.receive()
                    if signal is None:
                        continue

                    # Validate if schema defined
                    if self.SIGNAL_SCHEMA:
                        try:
                            self.validate_signal(signal)
                        except SignalValidationError as e:
                            self._log_warning(
                                "Signal validation failed",
                                trace_id=signal.trace_id,
                                error=str(e),
                            )
                            continue

                    # Process with timeout
                    start = time.time()
                    try:
                        output = await asyncio.wait_for(
                            self.process(signal),
                            timeout=self.config.process_timeout
                        )
                    except asyncio.TimeoutError:
                        self._record_error(
                            ProcessingTimeoutError(
                                "Process timeout",
                                neuron_name=self.name,
                                timeout_seconds=self.config.process_timeout,
                            ),
                            signal,
                        )
                        continue

                    latency = time.time() - start
                    self.metrics.record_processed(latency)

                    # Send
                    try:
                        await self.send(output, parent=signal)
                    except SignalRoutingError as e:
                        self._log_warning(
                            "Failed to send output",
                            trace_id=signal.trace_id,
                            error=str(e),
                        )

                    # Success - reset circuit breaker
                    self._record_success()
                    self.learning.record_activation()

                except asyncio.CancelledError:
                    raise
                except NeuronError as e:
                    # Known error type with context
                    self._record_error(e)
                    await asyncio.sleep(self.config.error_retry_delay)
                except Exception as e:
                    # Unknown error - wrap with context
                    wrapped = ProcessingFailedError(
                        f"Unexpected error: {e}",
                        neuron_name=self.name,
                        original_error=e,
                    )
                    self._record_error(wrapped)
                    await asyncio.sleep(self.config.error_retry_delay)

        except asyncio.CancelledError:
            pass
        finally:
            if self.running:
                self.running = False
                await self.teardown()

    def stop(self) -> None:
        """Signal the neuron to stop running."""
        self.running = False

    # ═══════════════════════════════════════════════════════════════════
    # QUEUE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════

    async def enqueue(self, signal: Signal) -> bool:
        """
        Add a signal to the input queue with backpressure handling.

        Args:
            signal: The signal to enqueue

        Returns:
            True if signal was enqueued, False if dropped
        """
        if self.input_queue is None:
            self._log_warning(
                "Cannot enqueue signal, queue not initialized",
                trace_id=signal.trace_id,
            )
            return False

        # High watermark warning
        queue_usage = self.input_queue.qsize() / self.config.queue_size
        if queue_usage > self.config.queue_high_watermark / 100:
            self.metrics.record_backpressure()
            self._log_warning(
                "Queue high watermark",
                trace_id=signal.trace_id,
                usage_percent=f"{queue_usage:.0%}",
            )

        # Handle full queue based on strategy
        if self.input_queue.full():
            strategy = self.config.backpressure_strategy

            if strategy == BackpressureStrategy.DROP_OLDEST:
                try:
                    dropped = self.input_queue.get_nowait()
                    self.metrics.record_dropped(dropped)
                    self._log_warning(
                        "Dropped oldest signal due to backpressure",
                        dropped_trace_id=dropped.trace_id,
                    )
                except asyncio.QueueEmpty:
                    pass

            elif strategy == BackpressureStrategy.DROP_NEWEST:
                self.metrics.record_dropped(signal)
                self._log_warning(
                    "Dropped new signal due to backpressure",
                    trace_id=signal.trace_id,
                )
                return False

            elif strategy == BackpressureStrategy.BLOCK:
                await self.input_queue.put(signal)
                self.metrics.record_received()
                return True

        # Enqueue
        try:
            self.input_queue.put_nowait(signal)
            self.metrics.record_received()
            return True
        except asyncio.QueueFull:
            self.metrics.record_dropped(signal)
            self._log_warning(
                "Signal dropped, queue full",
                trace_id=signal.trace_id,
            )
            return False

    # ═══════════════════════════════════════════════════════════════════
    # HEALTH CHECK
    # ═══════════════════════════════════════════════════════════════════

    def health_status(self) -> HealthStatus:
        """
        Determine current health status.

        Returns:
            HealthStatus enum value
        """
        if not self.running:
            return HealthStatus.STOPPED

        if self._circuit_open:
            return HealthStatus.CIRCUIT_OPEN

        if self.metrics.error_rate > 0.5:
            return HealthStatus.UNHEALTHY

        if self.input_queue:
            queue_usage = self.input_queue.qsize() / self.config.queue_size
            if queue_usage > 0.9:
                return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def health_check(self) -> dict:
        """
        Return health status and metrics.

        Returns:
            Dictionary with status, queue info, and metrics
        """
        queue_size = self.input_queue.qsize() if self.input_queue else 0
        queue_usage = queue_size / self.config.queue_size if self.config.queue_size else 0

        status = self.health_status()

        return {
            "name": self.name,
            "status": status.value,
            "running": self.running,
            "accepting": self.accepting,
            "circuit_open": self._circuit_open,
            "consecutive_errors": self._consecutive_errors,
            "queue_size": queue_size,
            "queue_usage": f"{queue_usage:.0%}",
            "activation_count": self.learning.activation_count,
            "metrics": self.metrics.to_dict(),
        }

    def __repr__(self) -> str:
        status = self.health_status().value
        return f"<{self.__class__.__name__} name={self.name} status={status}>"
