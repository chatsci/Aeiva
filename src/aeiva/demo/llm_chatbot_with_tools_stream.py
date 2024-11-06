# aeiva/demo/llm_chatbot_with_tools.py

#!/usr/bin/env python
# coding=utf-8
"""
Generalized chatbot using LLM with function call capabilities and tool integration via APIs.
"""

import os
import gradio as gr
import json
from dotenv import load_dotenv

from aeiva.llm.llm_client import LLMClient
from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.logger.logger import get_logger


# Setup logger
logger = get_logger(__name__, level="INFO")

# Load environment variables (API keys, etc.)
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_default_api_key_here")

# Initialize LLM client with function call capability
llm_gateway_config = LLMGatewayConfig(
    llm_model_name="gpt-4o-mini",  # Use the model that supports litellm's function calling and streaming
    llm_api_key=OPENAI_API_KEY,
    llm_base_url="https://api.openai.com/v1",
    llm_max_input_tokens=2048,
    llm_max_output_tokens=512,
    llm_use_async=True,    # Enable asynchronous mode
    llm_stream=True,       # Enable streaming
)
llm = LLMClient(llm_gateway_config)

# Load tool schema from JSON files
def load_tool_schema(api_name):
    current_path = os.path.dirname(os.path.abspath(__file__))
    # Adjust the project root as necessary
    project_root = os.path.abspath(os.path.join(current_path, "../../.."))
    path = os.path.join(
        project_root,
        f"src/aeiva/action/tool/api/function/{api_name}/{api_name}.json",
    )
    with open(path, "r") as file:
        return json.load(file)

# Gradio chatbot handler
async def bot(user_input, history):
    """
    Handles chatbot logic and dynamically invokes functions via LLM function calls.

    Args:
        user_input (str): The user's input.
        history (list): Conversation history.

    Yields:
        tuple: Updated history and an empty string to clear the input box.
    """
    try:
        # Append user's message to history
        history = history + [[user_input, None]]
        yield history, ''

        # Construct the messages
        messages = []
        for user_msg, assistant_msg in history[:-1]:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": assistant_msg})
        messages.append({"role": "user", "content": user_input})
        logger.info(f"Messages: {messages}")

        # Load tools
        tools = [
            load_tool_schema("test_operation"),
            load_tool_schema("get_paper_details"),
            # Add more tools as needed
        ]

        # Get the response stream
        stream = llm(messages, tools=tools)
        assistant_message = ''
        async for chunk in stream:
            assistant_message += chunk
            history[-1][1] = assistant_message
            yield history, ''
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        history[-1][1] = "An unexpected error occurred."
        yield history, ''

# Gradio interface
if __name__ == "__main__":
    with gr.Blocks(title="LLM Chatbot with Tools") as demo:
        chatbot = gr.Chatbot()
        with gr.Row():
            txt = gr.Textbox(
                show_label=False, placeholder="Ask a question or use tools via APIs"
            )

            txt.submit(
                bot,
                inputs=[txt, chatbot],
                outputs=[chatbot, txt],
            )
    demo.queue().launch()