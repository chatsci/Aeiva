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

Integration:
    This module integrates with aeiva.event.EventBus, converting between
    the Event class (used by EventBus) and Signal class (used by neurons).
"""

from typing import Any, Callable, List, Optional, Type, TYPE_CHECKING
from asyncio import Queue
from dataclasses import asdict
from uuid import uuid4
from datetime import timezone
import asyncio
import logging
import time

from .signal import Signal
from .state import IdentityState, WorkingState, LearningState
from .config import NeuronConfig, BackpressureStrategy
from .metrics import NeuronMetrics

if TYPE_CHECKING:
    from aeiva.event import EventBus, Event

logger = logging.getLogger(__name__)


class BaseNeuron:
    """
    Base implementation for all neurons.

    Structure:
        ├── State: identity, working, learning
        ├── Lifecycle: setup, teardown, graceful_shutdown
        ├── Core: receive, process, send
        ├── Request-Response: request
        ├── Persistence: save_state, load_state
        └── Execution: run_once, run_forever

    Class Attributes (override in subclasses):
        SUBSCRIPTIONS: Event patterns to subscribe to
        EMISSIONS: Event patterns this neuron emits (documentation)
        CONFIG_CLASS: Configuration class to use
        STATE_VERSION: For state migration on schema changes
    """

    # Override in subclasses
    SUBSCRIPTIONS: List[str] = []
    EMISSIONS: List[str] = []
    CONFIG_CLASS: Type[NeuronConfig] = NeuronConfig
    STATE_VERSION: int = 1

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
        """
        # Restore persisted state
        if self.storage:
            await self.load_state()

        # Create input queue
        self.input_queue = Queue(maxsize=self.config.queue_size)

        # Subscribe to events using callback pattern
        if self.events:
            patterns = self.SUBSCRIPTIONS or [f"{self.name}.*"]
            for pattern in patterns:
                callback = self.create_event_callback(pattern)
                self.events.subscribe(pattern, callback)
                self.subscribed_callbacks.append(callback)

            logger.info(f"{self.name} subscribed to {patterns}")

        logger.info(f"{self.name} setup complete")

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

        logger.info(f"{self.name} teardown complete")

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
        logger.info(f"{self.name} shutting down gracefully (timeout={timeout}s)")

        # Stop accepting new signals
        self.accepting = False

        # Wait for pending requests (1/3 of timeout)
        if self.working.pending_requests:
            pending = list(self.working.pending_requests.values())
            await asyncio.wait(pending, timeout=timeout / 3)

        # Drain queue (1/3 of timeout)
        deadline = time.time() + timeout / 3
        while self.input_queue and not self.input_queue.empty():
            if time.time() >= deadline:
                break
            try:
                signal = self.input_queue.get_nowait()
                remaining = deadline - time.time()
                await asyncio.wait_for(
                    self.process(signal),
                    timeout=max(0.1, remaining)
                )
            except (asyncio.TimeoutError, asyncio.QueueEmpty):
                break

        # Save state
        if self.storage:
            await self.save_state()

        # Stop running
        self.running = False
        await self.teardown()

        logger.info(f"{self.name} shutdown complete")

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
            await self.events.emit(**emit_args)

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
            TimeoutError: If no response within timeout

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
            raise TimeoutError(f"Request to {target} timed out after {timeout}s")
        finally:
            self.working.pending_requests.pop(request_id, None)

    async def handle_response(self, signal: Signal) -> None:
        """
        Handle an incoming response signal.

        This completes the future created by a previous request().
        """
        request_id = signal.data.get("request_id")
        if request_id and request_id in self.working.pending_requests:
            future = self.working.pending_requests[request_id]
            if not future.done():
                future.set_result(signal.data.get("result"))

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
        request_id = signal.data.get("request_id")
        reply_to = signal.data.get("reply_to")

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

        await self.storage.save(f"neuron:{self.name}", state)
        logger.debug(f"{self.name} state saved")

    async def load_state(self) -> bool:
        """
        Restore state from storage.

        Returns:
            True if state was restored, False if no state found
        """
        if not self.storage:
            return False

        state = await self.storage.load(f"neuron:{self.name}")
        if state is None:
            return False

        # Version check
        if state.get("version", 1) != self.STATE_VERSION:
            logger.warning(f"{self.name} state version mismatch, skipping load")
            return False

        if "identity" in state:
            self.identity = IdentityState(**state["identity"])

        if "learning" in state:
            self.learning = LearningState(**state["learning"])

        logger.info(f"{self.name} state restored")
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
        """
        if signal is None:
            signal = await self.receive()
            if signal is None:
                return None

        output = await self.process(signal)
        await self.send(output, parent=signal)
        return output

    async def run_forever(self) -> None:
        """
        Run the neuron's main loop until stopped.

        This is the primary execution method. It:
            1. Calls setup()
            2. Loops: receive → process → send
            3. Handles errors with retry logic
            4. Calls teardown() when stopped
        """
        await self.setup()
        self.running = True
        consecutive_errors = 0

        try:
            while self.running:
                try:
                    # Receive
                    signal = await self.receive()
                    if signal is None:
                        continue

                    # Process with timeout
                    start = time.time()
                    try:
                        output = await asyncio.wait_for(
                            self.process(signal),
                            timeout=self.config.process_timeout
                        )
                    except asyncio.TimeoutError:
                        logger.error(f"{self.name} process timeout")
                        self.metrics.record_error(TimeoutError("process timeout"))
                        continue

                    latency = time.time() - start
                    self.metrics.record_processed(latency)

                    # Send
                    await self.send(output, parent=signal)

                    # Update learning state
                    self.learning.record_activation()
                    consecutive_errors = 0

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    consecutive_errors += 1
                    self.metrics.record_error(e)
                    logger.exception(f"{self.name} error: {e}")

                    if consecutive_errors >= self.config.max_consecutive_errors:
                        logger.error(f"{self.name} circuit breaker tripped")
                        break

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

        Returns:
            True if signal was enqueued, False if dropped
        """
        # High watermark warning
        queue_usage = self.input_queue.qsize() / self.config.queue_size
        if queue_usage > self.config.queue_high_watermark / 100:
            self.metrics.record_backpressure()
            logger.warning(f"{self.name} queue at {queue_usage:.0%}")

        # Handle full queue based on strategy
        if self.input_queue.full():
            strategy = self.config.backpressure_strategy

            if strategy == BackpressureStrategy.DROP_OLDEST:
                try:
                    dropped = self.input_queue.get_nowait()
                    self.metrics.record_dropped(dropped)
                except asyncio.QueueEmpty:
                    pass

            elif strategy == BackpressureStrategy.DROP_NEWEST:
                self.metrics.record_dropped(signal)
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
            return False

    # ═══════════════════════════════════════════════════════════════════
    # HEALTH CHECK
    # ═══════════════════════════════════════════════════════════════════

    def health_check(self) -> dict:
        """
        Return health status and metrics.

        Returns:
            Dictionary with status, queue info, and metrics
        """
        queue_size = self.input_queue.qsize() if self.input_queue else 0
        queue_usage = queue_size / self.config.queue_size if self.config.queue_size else 0

        # Determine status
        if not self.running:
            status = "stopped"
        elif self.metrics.error_rate > 0.5:
            status = "unhealthy"
        elif queue_usage > 0.9:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "name": self.name,
            "status": status,
            "running": self.running,
            "accepting": self.accepting,
            "queue_size": queue_size,
            "queue_usage": f"{queue_usage:.0%}",
            "activation_count": self.learning.activation_count,
            "metrics": self.metrics.to_dict(),
        }

    def __repr__(self) -> str:
        status = "running" if self.running else "stopped"
        return f"<{self.__class__.__name__} name={self.name} status={status}>"
