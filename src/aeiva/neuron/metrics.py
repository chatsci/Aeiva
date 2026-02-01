"""
Metrics: Observability and health monitoring for neurons.

Every neuron collects metrics about its performance, enabling:
    - Health checks and status dashboards
    - Performance debugging
    - Automatic scaling decisions
    - Alert triggering

Design Philosophy:
    - Metrics are lightweight and always-on
    - Sliding window for latency to bound memory
    - No external dependencies (pure Python)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class NeuronMetrics:
    """
    Performance metrics for a single neuron.

    Counters:
        signals_received: Total signals received
        signals_processed: Total signals successfully processed
        signals_dropped: Total signals dropped due to backpressure
        errors: Total processing errors
        backpressure_events: Times queue hit high watermark

    Latency:
        process_latencies: Sliding window of recent processing times
    """

    name: str

    # Counters
    signals_received: int = 0
    signals_processed: int = 0
    signals_dropped: int = 0
    errors: int = 0
    backpressure_events: int = 0

    # Latency tracking (sliding window)
    process_latencies: List[float] = field(default_factory=list)
    max_latency_samples: int = 100

    def record_received(self) -> None:
        """Record that a signal was received."""
        self.signals_received += 1

    def record_processed(self, latency: float) -> None:
        """Record successful processing with its latency."""
        self.signals_processed += 1
        self.process_latencies.append(latency)
        if len(self.process_latencies) > self.max_latency_samples:
            self.process_latencies.pop(0)

    def record_dropped(self, signal: Any) -> None:
        """Record that a signal was dropped."""
        self.signals_dropped += 1
        trace_id = getattr(signal, "trace_id", "unknown")
        logger.warning(f"{self.name} dropped signal: {trace_id}")

    def record_error(self, error: Exception) -> None:
        """Record a processing error."""
        self.errors += 1

    def record_backpressure(self) -> None:
        """Record a backpressure event."""
        self.backpressure_events += 1

    @property
    def avg_latency(self) -> float:
        """Average processing latency in seconds."""
        if not self.process_latencies:
            return 0.0
        return sum(self.process_latencies) / len(self.process_latencies)

    @property
    def p95_latency(self) -> float:
        """95th percentile processing latency in seconds."""
        if not self.process_latencies:
            return 0.0
        sorted_latencies = sorted(self.process_latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    @property
    def error_rate(self) -> float:
        """Proportion of signals that resulted in errors."""
        if self.signals_received == 0:
            return 0.0
        return self.errors / self.signals_received

    @property
    def drop_rate(self) -> float:
        """Proportion of signals that were dropped."""
        if self.signals_received == 0:
            return 0.0
        return self.signals_dropped / self.signals_received

    @property
    def throughput(self) -> float:
        """Signals processed per second (based on latency)."""
        if self.avg_latency == 0:
            return 0.0
        return 1.0 / self.avg_latency

    def to_dict(self) -> Dict[str, Any]:
        """Export metrics as a dictionary for serialization."""
        return {
            "name": self.name,
            "signals_received": self.signals_received,
            "signals_processed": self.signals_processed,
            "signals_dropped": self.signals_dropped,
            "errors": self.errors,
            "error_rate": f"{self.error_rate:.2%}",
            "drop_rate": f"{self.drop_rate:.2%}",
            "avg_latency_ms": f"{self.avg_latency * 1000:.2f}",
            "p95_latency_ms": f"{self.p95_latency * 1000:.2f}",
            "backpressure_events": self.backpressure_events,
        }

    def reset(self) -> None:
        """Reset all metrics to zero."""
        self.signals_received = 0
        self.signals_processed = 0
        self.signals_dropped = 0
        self.errors = 0
        self.backpressure_events = 0
        self.process_latencies.clear()
