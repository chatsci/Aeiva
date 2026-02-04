"""
Cognition module for intelligent agent systems.

This module provides cognitive processing capabilities including:
- Cognition: Central orchestrator neuron (wraps Brain)
- Brain: Abstract thinking interface (LLMBrain uses litellm)
- Emotion: Emotional processing subsystem
- WorldModel: World state modeling

Architecture:
    Cognition (neuron)
        └── Brain (abstract)
            └── LLMBrain (concrete)
                └── LLMClient
                    └── litellm → OpenAI/Anthropic/etc.

Example usage:
    from aeiva.cognition import Cognition
    from aeiva.cognition.brain.llm_brain import LLMBrain

    # Create brain
    brain = LLMBrain({'llm_gateway_config': {...}})
    brain.setup()

    # Create cognition neuron
    cognition = Cognition(name="cognition", brain=brain, event_bus=bus)
    await cognition.setup()
"""

# Main cognition neuron
from aeiva.cognition.cognition import Cognition, CognitionConfig, CognitionState

# Response processing components
from aeiva.cognition.response_classifier import (
    ResponseClassifier,
    ResponseType,
    ClassificationResult,
)
from aeiva.cognition.stream_buffer import StreamBuffer, FlushDecision

# Re-export submodules for convenience
from aeiva.cognition import brain
from aeiva.cognition import emotion
from aeiva.cognition import world_model

__all__ = [
    # Main neuron
    "Cognition",
    "CognitionConfig",
    "CognitionState",

    # Response processing
    "ResponseClassifier",
    "ResponseType",
    "ClassificationResult",
    "StreamBuffer",
    "FlushDecision",

    # Submodules
    "brain",
    "emotion",
    "world_model",
]
