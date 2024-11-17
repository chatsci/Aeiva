# agent.py

import os
from datetime import datetime, timezone
from typing import Any
import asyncio
from aeiva.cognition.input_interpreter.simple_input_interpreter import SimpleInputInterpreter
from aeiva.cognition.output_orchestrator.simple_output_orchestrator import SimpleOutputOrchestrator
from aeiva.cognition.memory.simple_memory import SimpleMemory
from aeiva.cognition.emotion.simple_emotion import SimpleEmotion
from aeiva.cognition.world_model.simple_world_model import SimpleWorldModel
from aeiva.cognition.brain.llm_brain import LLMBrain
from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.agent.agent import Agent
import litellm

# Main function
def main():
    # Define configurations
    perception_config = {
        "sensors": [
            {
                "sensor_name": "percept_terminal_input",
                "sensor_params": {"prompt_message": "You: "}
            }
        ]
    }

    # Load environment variables and set up LLMBrain
    API_KEY = os.getenv('OPENAI_API_KEY')
    config = LLMGatewayConfig(
        llm_api_key=API_KEY,
        llm_model_name="gpt-4o",
        llm_temperature=0.7,  
        llm_max_output_tokens=10000,
        # llm_logging_level="info",
        llm_stream=True
    )
    # litellm.drop_params=True # o1-mini doesn't support temperature parameter and so on.

    llm_brain = LLMBrain(config)
    cognition_components = {
        "input_interpreter": SimpleInputInterpreter(),
        "brain": llm_brain,  # Assuming llm_brain is an instance of your Brain class
        "output_orchestrator": SimpleOutputOrchestrator(),
        "memory": SimpleMemory(),
        "emotion": SimpleEmotion(),
        "world_model": SimpleWorldModel(),
        "config": None
    }

    action_config = {
        # Include any configurations needed for your ActionSystem
        "tools": [
            # "test_operation",
            "get_system_info",
            "get_package_root",
            "get_user_home_path",
            "open_application",
            "close_application",
            "percept_terminal_input",
            "play_music",
            "stop_music",
            "take_screenshot",
            "create_file_or_folder",
            "delete_file",
            "edit_file",
            "find_file",
            "list_files",
            "open_file_or_folder",
            "read_file",
            "rename_file",
            "search_file_or_folder",
            "write_file",
            "analyze_gui",
            "analyze_gui_by_ocr",
            "click_mouse",
            "click_on_element",
            "move_mouse",
            "operate_computer",
            "scroll",
            "type_into_element",
            "type_keyboard",
            "click_webpage_element",
            "crawl",
            "execute_js_script_on_webpage",
            "get_webpage_details",
            "get_webpage_elements",
            "navigate_browser_history",
            "navigate_to_webpage",
            "refresh_webpage",
            "scrape",
            "scroll_webpage",
            "type_text_in_webpage_element",
            "web_search"
        ]
    }

    # Create agent instance
    agent = Agent(perception_config, cognition_components, action_config)
    agent.setup()

    # Run the agent
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()