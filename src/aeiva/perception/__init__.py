"""
AEIVA Perception Module

This module handles sensory input processing using the neuron architecture.

Main Components:
    - PerceptionNeuron: The primary perception handler (neuron-based)
    - Stimuli: Structured sensory data
    - Sensor: Base class for input sensors

Usage:
    from aeiva.perception import PerceptionNeuron, Stimuli

    neuron = PerceptionNeuron(config=perception_config, event_bus=bus)
    await neuron.setup()
    await neuron.start_sensors()

Deprecated:
    - PerceptionSystem: Use PerceptionNeuron instead
"""

from aeiva.perception.perception import PerceptionNeuron, PerceptionNeuronConfig
from aeiva.perception.stimuli import Stimuli
from aeiva.perception.sensation import Signal as PerceptionSignal

__all__ = [
    "PerceptionNeuron",
    "PerceptionNeuronConfig",
    "Stimuli",
    "PerceptionSignal",
]
