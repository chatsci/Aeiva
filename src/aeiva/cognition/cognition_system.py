# File: cognition/cognition_system.py

from typing import Any, Optional, List, Dict, Union, AsyncGenerator
from aeiva.cognition.input_interpreter.input_interpreter import InputInterpreter
from aeiva.cognition.output_orchestrator.output_orchestrator import OutputOrchestrator
from aeiva.cognition.brain.brain import Brain
from aeiva.cognition.memory.memory import Memory
from aeiva.cognition.emotion.emotion import Emotion
from aeiva.cognition.world_model.world_model import WorldModel
from aeiva.perception.stimuli import Stimuli
from aeiva.cognition.observation import Observation
from aeiva.cognition.thought import Thought
from aeiva.action.plan import Plan

from aeiva.cognition.input_interpreter.simple_input_interpreter import SimpleInputInterpreter
from aeiva.cognition.output_orchestrator.simple_output_orchestrator import SimpleOutputOrchestrator
from aeiva.cognition.brain.llm_brain import LLMBrain
from aeiva.cognition.memory.memory_palace import MemoryPalace
from aeiva.cognition.emotion.simple_emotion import SimpleEmotion
from aeiva.cognition.world_model.simple_world_model import SimpleWorldModel


class CognitionSystem:
    """
    Processes Stimuli into Observations, uses the Brain to generate Thoughts, and orchestrates output into Plans.
    """
    def __init__(self, config: Dict):
        self.config_dict = config
        self.config = None
        self.input_interpreter = None
        self.brain = None
        self.output_orchestrator = None
        self.memory = None
        self.emotion = None
        self.world_model = None
        self.state = self.init_state()

    def init_state(self) -> Dict[str, Any]:
        return {
            "cognitive_state": None,
            "last_input": None,
            "last_output": None
        }

    def setup(self) -> None:
        """
        Set up the cognition system's components.
        """
        self.brain = LLMBrain(config=self.config_dict)
        self.memory = MemoryPalace(config=self.config_dict)
        self.emotion = SimpleEmotion()  # TODO: replace
        self.world_model = SimpleWorldModel()  # TODO: replace
        self.input_interpreter = SimpleInputInterpreter()  # TODO: replace
        self.output_orchestrator = SimpleOutputOrchestrator()  # TODO: replace
        
        self.brain.setup()
        self.memory.setup()
        self.world_model.setup()
        self.emotion.setup()
        self.input_interpreter.setup()
        self.output_orchestrator.setup()

    def handle_error(self, error: Exception) -> None:
        print(f"CognitionSystem encountered an error: {error}")
    
    async def think(
            self,
            stimuli: Stimuli,
            tools: List[Dict[str, Any]] = None,
            stream: bool=False,
            use_async: bool=False
            ) -> AsyncGenerator[str, None]:
        """
        Processes stimuli and produces a thought or plan.

        Args:
            stimuli (Stimuli): The input stimuli.
            stream (bool): Whether to use streaming mode.
            tools (List[Dict[str, Any]]): Optional tools for function calls.

        Yields:
            str: Chunks of the assistant's response.
        """
        self.state["last_input"] = stimuli

        # Step 1: Use InputInterpreter to process stimuli into observation
        if self.input_interpreter.gate(stimuli):
            observation = await self.input_interpreter.interpret(stimuli)
        else:
            # Directly pass stimuli as observation (assuming it's acceptable)
            observation = Observation(data=stimuli.to_dict())

        # Step 2: Brain processes the observation into a thought or plan
        brain_input = [{"role": "user", "content": observation.data}]
        # Initiate brain processing
        response_gen = self.brain.think(brain_input, tools=tools, stream=stream, use_async=use_async)

        async for chunk in response_gen:
            if isinstance(chunk, str):
                # Streaming chunk or full response in non-streaming mode
                yield chunk
            elif isinstance(chunk, Thought):
                thought = chunk
                self.state["cognitive_state"] = thought

                # Step 3: Use OutputOrchestrator if applicable
                if self.output_orchestrator.gate(thought):
                    plan = await self.output_orchestrator.orchestrate(thought)
                    self.state["last_output"] = plan
                    yield plan.content if hasattr(plan, 'content') else str(plan)
                else:
                    self.state["last_output"] = thought
                    yield thought.content
            elif isinstance(chunk, Plan):
                plan = chunk
                self.state["last_output"] = plan
                yield plan.content if hasattr(plan, 'content') else str(plan)
            else:
                # Handle unexpected chunk types
                #logger.warning(f"Unexpected chunk type: {type(chunk)}")
                yield str(chunk)