# File: cognition/cognition_system.py

from typing import Any, Optional, List, Dict, Union
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

class CognitionSystem:
    """
    Processes Stimuli into Observations, uses the Brain to generate Thoughts, and orchestrates output into Plans.
    """
    def __init__(self,
                 input_interpreter: InputInterpreter,
                 brain: Brain,
                 output_orchestrator: OutputOrchestrator,
                 memory: Memory,
                 emotion: Emotion,
                 world_model: WorldModel,
                 config: Optional[Any] = None):
        self.config = config
        self.input_interpreter = input_interpreter
        self.brain = brain
        self.output_orchestrator = output_orchestrator
        self.memory = memory
        self.emotion = emotion
        self.world_model = world_model
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
        self.input_interpreter.setup()
        self.brain.setup()
        self.memory.setup()
        self.emotion.setup()
        self.world_model.setup()
        self.output_orchestrator.setup()

    async def think(self, stimuli: Stimuli, stream: bool=False, tools: List[Dict[str, Any]] = None) -> Union[Thought, Plan]:
        """
        Processes stimuli and produces a thought or plan.
        """
        self.state["last_input"] = stimuli

        # Step 1: Use InputInterpreter to process stimuli into observation
        if self.input_interpreter.gate(stimuli):
            observation = await self.input_interpreter.interpret(stimuli)
        else:
            # Directly pass stimuli as observation (assuming it's acceptable)
            observation = Observation(data=stimuli.to_dict())

        # Step 2: Brain processes the observation into a thought
        
        brain_input = [{"role": "user", "content": observation.data}]
        # print("############# observation is: ", brain_input)
        thought_content = await self.brain.think(brain_input, stream, tools=tools)
        thought = Thought(content=thought_content)

        self.state["cognitive_state"] = thought

        # # Step 3: Update Memory, Emotion, and WorldModel
        # await self.memory.store({
        #     'observation': observation.to_dict(),
        #     'thought': thought.to_dict()
        # })
        # await self.emotion.update({
        #     'observation': observation.to_dict(),
        #     'thought': thought.to_dict()
        # })
        # await self.world_model.update({
        #     'observation': observation.to_dict(),
        #     'thought': thought.to_dict()
        # })

        # Step 4: Use OutputOrchestrator to produce a plan or direct response
        if self.output_orchestrator.gate(thought):
            plan = await self.output_orchestrator.orchestrate(thought)
            self.state["last_output"] = plan
            return plan
        else:
            # Directly return the thought (e.g., as a response to the user)
            self.state["last_output"] = thought
            #print("thought is===", thought)  # TODO: this is for debug
            return thought

    def handle_error(self, error: Exception) -> None:
        print(f"CognitionSystem encountered an error: {error}")