import asyncio
import logging
from aeiva.perception.perception_system import PerceptionSystem
from aeiva.perception.sensor import Sensor
from aeiva.cognition.brain.llm_brain import LLMBrain
from aeiva.cognition.brain.llm.llm_gateway_config import LLMGatewayConfig
import os

# # Configure logging
# logging.basicConfig(level=logging.INFO)

# Load environment variables and set up LLMBrain
API_KEY = os.getenv('OPENAI_API_KEY')
config = LLMGatewayConfig(
    llm_api_key=API_KEY,
    llm_model_name="gpt-4-turbo",
    llm_temperature=0.7,
    llm_max_output_tokens=1000,
    llm_logging_level="info",
    llm_stream=True
)
llm_brain = LLMBrain(config)


async def handle_observation(stimuli):
    """
    Processes stimuli using the cognition system and outputs the response.
    """
    for signal in stimuli.signals:
        user_input = signal.data
        stimuli_data = [{"role": "user", "content": user_input}]
        response = await llm_brain.think(stimuli_data, stream=True)
        print(f"LLM Response: {response}")


# Define sensors
sensor_config = [
    {
        "sensor_name": "percept_terminal_input",
        "sensor_params": {"prompt_message": "You: "}
    }
]
sensors = [Sensor(cfg["sensor_name"], cfg["sensor_params"]) for cfg in sensor_config]

# Initialize PerceptionSystem
perception_system = PerceptionSystem(config={"sensors": sensor_config})
perception_system.setup()

# Get the observation stream
observation_stream = perception_system.perceive()

# Subscribe to the observation stream
observation_stream.subscribe(
    on_next=lambda stimuli: asyncio.run(handle_observation(stimuli)),
    on_error=lambda e: logging.error(f"Error: {e}"),
    on_completed=lambda: logging.info("Perception stream completed.")
)
