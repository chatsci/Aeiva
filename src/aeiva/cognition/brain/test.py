import asyncio
from dotenv import load_dotenv
import os
from aeiva.cognition.brain.llm_brain import LLMBrain
from aeiva.llm.llm_gateway_config import LLMGatewayConfig

# Load environment variables from .env
load_dotenv()

# Fetch the API key from environment variables
API_KEY = os.getenv('OPENAI_API_KEY')

if not API_KEY:
    raise ValueError("API key is missing. Please set it in the .env file.")

async def test_llm_brain():
    # Initialize configuration for LLMBrain
    config = LLMGatewayConfig(
        llm_api_key=API_KEY,
        llm_model_name="gpt-3.5-turbo",
        llm_temperature=0.7,
        llm_max_output_tokens=100,
        llm_logging_level="info",
        llm_stream=False  # Start with non-streaming mode
    )

    # Create an instance of LLMBrain
    llm_brain = LLMBrain(config)
    
    # Set up the brain
    await llm_brain.setup()

    # Define some input stimuli (conversation)
    stimuli = [
        {
            "role": "user",
            "content": "What is the capital of France?"
        }
    ]

    # Test async non-streaming mode
    print("Testing async non-streaming mode...")
    response = await llm_brain.think(stimuli, stream=False)
    print("Response (non-streaming):", response)

    # Enable streaming in the config for the next test
    config.llm_stream = True

    # Test async streaming mode
    print("\nTesting async streaming mode...")
    await llm_brain.think(stimuli, stream=True)

# Run the test
if __name__ == "__main__":
    asyncio.run(test_llm_brain())
