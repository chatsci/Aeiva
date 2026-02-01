"""
Emotion module for intelligent agent systems.

This module provides a single PAD-based EmotionNeuron implementation.

Example usage:
    from aeiva.cognition.emotion import EmotionNeuron

    neuron = EmotionNeuron(name="emotion", event_bus=bus)

    await neuron.setup()
"""

from aeiva.cognition.emotion.emotion import EmotionNeuron, EmotionNeuronConfig, PADState

__all__ = [
    "EmotionNeuron",
    "EmotionNeuronConfig",
    "PADState",
]
