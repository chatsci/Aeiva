"""
Brain module for cognitive processing.

This module provides the Brain abstraction for cognitive processing:
- Brain: Abstract base class defining the thinking interface
- LLMBrain: Concrete implementation using LLM (via litellm)

Architecture:
    Brain (abstract)
        └── LLMBrain (concrete)
            └── LLMClient
                └── litellm → OpenAI/Anthropic/etc.

Example usage:
    from aeiva.cognition.brain import Brain, LLMBrain

    # Create and configure brain
    brain = LLMBrain({
        'llm_gateway_config': {
            'llm_model_name': 'gpt-4o',
            'llm_api_key': 'sk-...',
        }
    })
    brain.setup()

    # Use brain for thinking
    async for response in brain.think([{"role": "user", "content": "Hello"}]):
        print(response)
"""

from aeiva.cognition.brain.base_brain import Brain
from aeiva.cognition.brain.llm_brain import LLMBrain

__all__ = [
    "Brain",
    "LLMBrain",
]
