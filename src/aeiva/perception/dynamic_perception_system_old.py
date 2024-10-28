import importlib
from typing import Any, Dict, Optional, Callable
import asyncio
from aeiva.perception.sensation import Signal
from aeiva.perception.stimuli import Stimuli
from aeiva.perception.perception_system_rx import PerceptionSystem
from aeiva.event.event import Event, EventSource
from aeiva.event.event_bus import EventBus
from aeiva.action.tool.tool import Tool


class DynamicPerceptionSystem(PerceptionSystem):
    """
    A concrete implementation of the PerceptionSystem that dynamically loads and calls perception functions 
    from the config, captures raw sensory data using tools, and converts them into structured stimuli.
    Utilizes event-based communication for the perception process.
    """

    def __init__(self, config: Dict[str, Any], event_bus: EventBus):
        super().__init__(config)
        self.perception_functions = config.get("perception_functions", [])
        self.event_bus = event_bus  # EventBus for event-based communication
        self.perception_function_map: Dict[str, Callable] = {}  # Maps function names to tool API execution
        self.event_bus.subscribe(EventSource.USER, self.capture)  # Subscribe to input_detected event
        self.event_bus.subscribe(EventSource.AGENT, self.process)  # Subscribe to signal_captured event

    def init_state(self) -> Dict[str, Any]:
        return {
            "raw_signals": [],
            "observations": None
        }

    async def setup(self) -> None:
        """
        Setup function that dynamically loads the perception functions specified in the config.
        """
        for func_name in self.perception_functions:
            try:
                self.perception_function_map[func_name] = func_name  # Store the function name for later use
            except Exception as e:
                self.handle_error(e)
                raise Exception(f"Error loading perception function tool: {func_name}. {e}")

    async def capture(self, event: Event) -> None:
        """
        Capture function triggered by 'input_detected' event.
        Calls perception tools and collects their output as signals.
        """
        raw_signals = []
        prompt_message = event.message.get("raw_data", {}).get("prompt_message", "Please enter input: ")

        for func_name in self.perception_function_map.keys():
            try:
                # Call the tool to get input
                signal_data = await Tool(func_name).execute(params={"prompt_message": prompt_message})  # Pass the prompt message
                signal = Signal(data=signal_data, name=func_name)
                raw_signals.append(signal)
            except Exception as e:
                self.handle_error(e)
                raise Exception(f"Error during perception function '{func_name}': {e}")

        if not raw_signals:
            print("No signals were captured.")
            return

        self.state["raw_signals"] = raw_signals

        # Publish a signal_captured event after capturing raw signals
        signal_event = Event(
            source=EventSource.AGENT,
            message={"signals": raw_signals}
        )
        
        await self.event_bus.publish(signal_event)

    async def process(self, event: Event) -> None:
        """
        Process function triggered by 'signal_captured' event.
        Converts captured raw signals into structured stimuli.
        """
        signals = event.message.get("signals", [])
        if not signals:
            print("No signals captured to process.")
            return  # Avoid raising an error here for a more graceful handling

        # Create stimuli from the captured signals
        stimuli = Stimuli(signals=signals)
        self.state["observations"] = stimuli

        # Publish observation_updated event after processing
        observation_event = Event(
            source=EventSource.PERCEPTION_SYSTEM,  #!~!!!!!!!!!!!! change later
            message={"observation": stimuli}
        )
        await self.event_bus.publish(observation_event)

    def get_observations(self) -> Optional[Stimuli]:
        """
        Retrieve the current observations (processed stimuli) from the Perception System.
        """
        return self.state.get("observations", None)

    def handle_error(self, error: Exception) -> None:
        """
        Default error handling method for the Perception System.
        """
        print(f"Error in PerceptionSystem: {error}")