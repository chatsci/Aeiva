# test_embedder.py

from aeiva.embedding.embedder_config import EmbedderConfig
from aeiva.embedding.embedder import Embedder
import asyncio
import os
from dotenv import load_dotenv


# Load environment variables (API keys, etc.)
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_default_api_key_here")


def test_sync_embedding():
    """
    Test the synchronous embedding functionality.
    """
    # Example with OpenAI
    config = EmbedderConfig(
        provider_name='openai',
        model_name='text-embedding-ada-002',
        api_key=OPENAI_API_KEY  # Replace with your actual API key
    )
    embedder = Embedder(config)

    input_text = "Hello, this is a test of the embedding module."
    response = embedder.embed(input_text)
    print("Synchronous Embedding Response:")
    print(response)


def test_async_embedding():
    """
    Test the asynchronous embedding functionality.
    """
    # Example with OpenAI
    config = EmbedderConfig(
        provider_name='openai',
        model_name='text-embedding-ada-002',
        api_key=OPENAI_API_KEY  # Replace with your actual API key
    )
    embedder = Embedder(config)

    async def run():
        input_text = "Hello, this is an asynchronous test of the embedding module."
        response = await embedder.aembed(input_text)
        print("Asynchronous Embedding Response:")
        print(response)

    asyncio.run(run())


if __name__ == '__main__':
    test_sync_embedding()
    test_async_embedding()