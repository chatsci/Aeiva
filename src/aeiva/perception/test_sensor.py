import asyncio
import reactivex as rx
from reactivex import operators as ops
from dotenv import load_dotenv
import os
from aeiva.cognition.brain.llm_brain import LLMBrain
from aeiva.cognition.brain.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.perception.sensor import Sensor

# Load environment variables from .env
load_dotenv()
API_KEY = os.getenv('OPENAI_API_KEY')
if not API_KEY:
    raise ValueError("API key is missing. Please set it in the .env file.")

# # for debug
# import litellm
# litellm.set_verbose=True

# Set up LLMBrain
config = LLMGatewayConfig(
    llm_api_key=API_KEY,
    llm_model_name="gpt-4-turbo",
    llm_temperature=0.7,
    llm_max_output_tokens=1000,
    llm_logging_level="info",
    llm_stream=False  # Start with non-streaming mode
)
llm_brain = LLMBrain(config)

async def get_llm_response(user_input: str) -> str:
    global llm_brain
    # Define some input stimuli (conversation)
    stimuli = [
        {
            "role": "user",
            "content": user_input
        }
    ]

    # Get the response from the LLM
    response = await llm_brain.think(stimuli, stream=True)
    print()
    return response


# create sensor from api name and Optional api params.
sensor = Sensor("percept_terminal_input", {"prompt_message": "User: "})
print("Type your messages (type 'exit' or 'quit' to stop):")

input_stream = sensor.percept()  # Get the input stream

# Subscribing to the input stream with the LLM response
input_stream.subscribe(
    on_next=lambda user_input: asyncio.run(get_llm_response(user_input)),  # Call LLM with user input
    on_error=lambda e: print(f"Error: {e}"),
    on_completed=lambda: print("Input stream completed.")
)