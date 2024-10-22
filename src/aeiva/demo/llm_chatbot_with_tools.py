# aeiva/demo/llm_chatbot_with_tools.py

#!/usr/bin/env python
# coding=utf-8
"""
Generalized chatbot using LLM with function call capabilities and tool integration via APIs.
"""

import os
import gradio as gr
import json
import asyncio
from dotenv import load_dotenv

from aeiva.cognition.brain.llm.llm_client import LLMClient
from aeiva.cognition.brain.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.logger.logger import get_logger


# Setup logger
logger = get_logger(__name__, level="INFO")

# Load environment variables (API keys, etc.)
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_default_api_key_here")

# Initialize LLM client with function call capability
llm_gateway_config = LLMGatewayConfig(
    llm_model_name="gpt-3.5-turbo-1106",  # Use the model that supports litellm's function calling
    llm_api_key=OPENAI_API_KEY,
    llm_base_url="https://api.openai.com/v1",
    llm_max_input_tokens=2048,
    llm_max_output_tokens=512,
    llm_use_async=True,    # Enable asynchronous mode
    llm_stream=False,      # Disable streaming because function calling in streaming mode is not supported
)
llm = LLMClient(llm_gateway_config)

# Load tool schema from JSON files
def load_tool_schema(api_name):
    current_path = os.path.dirname(os.path.abspath(__file__))
    # Traverse up to find the project root (assuming project root is 4 levels up)
    project_root = os.path.abspath(os.path.join(current_path, "../../.."))
    path = os.path.join(
        project_root,
        f"src/aeiva/action/tools/api/function/{api_name}/{api_name}.json",
    )
    with open(path, "r") as file:
        return json.load(file)

# Helper to construct messages from history
def construct_messages(history):
    messages = []
    for entry in history:
        role = entry['role']
        content = entry['content']
        messages.append({"role": role, "content": content})
    return messages

# Gradio chatbot handler
async def bot(history):
    """
    Handles chatbot logic and dynamically invokes functions via LLM function calls.

    Args:
        history (list): Conversation history.

    Returns:
        list: Updated conversation history with the bot's response.
    """
    try:
        # Construct the messages
        messages = construct_messages(history)
        logger.info(f"Messages: {messages}")

        # Load tools (test_operation and arxiv_json)
        tools = [
            load_tool_schema("test_operation"),
            load_tool_schema("get_paper_details"),
            # Add more tools as needed
        ]

        # Get the response
        response = await llm(messages, tools=tools)
        # Update the assistant's last message in the history
        history[-1]['content'] = response
        return history

    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        history[-1]['content'] = "An unexpected error occurred."
        return history

# Gradio interface
if __name__ == "__main__":
    with gr.Blocks(title="LLM Chatbot with Tools") as demo:
        chatbot = gr.Chatbot([], elem_id="chatbot", type='messages')

        with gr.Row():
            txt = gr.Textbox(
                show_label=False, placeholder="Ask a question or use tools via APIs"
            )

            # Adjust the submit action to handle async function
            def user_input_submit(user_input, history):
                # Append user's message to history
                history = history + [{'role': 'user', 'content': user_input}, {'role': 'assistant', 'content': ''}]
                return history

            txt.submit(
                user_input_submit,
                [txt, chatbot],
                [chatbot],
            ).then(
                bot,
                chatbot,
                chatbot,
            )

    demo.queue().launch()