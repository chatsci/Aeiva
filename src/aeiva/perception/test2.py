import asyncio
import reactivex as rx
from reactivex import operators as ops
from typing import Any
import logging
import os

# Assume necessary imports and class definitions from previous snippets
from dotenv import load_dotenv
from aeiva.cognition.brain.llm_brain import LLMBrain
from aeiva.cognition.brain.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.perception.sensor import Sensor
from aeiva.perception.percept_system import PerceptionSystem
from aeiva.perception.stimuli import Stimuli

# Configure logging
logging.basicConfig(level=logging.INFO)

async def main():
    # Load environment variables from .env
    load_dotenv()

    # Fetch the API key from environment variables
    API_KEY = os.getenv('OPENAI_API_KEY')

    if not API_KEY:
        raise ValueError("API key is missing. Please set it in the .env file.")

    config = LLMGatewayConfig(
        llm_api_key=API_KEY,
        llm_model_name="gpt-4-turbo",
        llm_temperature=0.7,
        llm_max_output_tokens=1000,
        llm_logging_level="info",
        llm_stream=False  # Start with non-streaming mode
    )

    # Create an instance of LLMBrain
    llm_brain = LLMBrain(config)


    # Define your sensor functions
    async def async_user_input():
        while True:
            user_input = await asyncio.get_event_loop().run_in_executor(None, input, "You: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            yield user_input

    # Create sensors
    sensor = Sensor(async_user_input)

    # Initialize PerceptionSystem
    perception_system = PerceptionSystem(sensors=[sensor])
    await perception_system.setup()

    # Get the observation stream
    observation_stream = perception_system.perceive()

    # Handle observations
    async def handle_observation(stimuli: Stimuli):
        # Process the stimuli with the cognition system
        response = await llm_brain.think([stimuli], stream=True)
        print(f"LLM Response: {response}")

    # Subscribe to the observation stream
    observation_stream.subscribe(
        on_next=lambda stimuli: asyncio.create_task(handle_observation(stimuli)),
        on_error=lambda e: logging.error(f"Error: {e}"),
        on_completed=lambda: logging.info("Perception stream completed.")
    )

    # Keep the event loop running
    while True:
        await asyncio.sleep(1)

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())