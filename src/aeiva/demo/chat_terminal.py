# run_agent.py

import asyncio
import logging
from aeiva.agent.agent import Agent  # Ensure Agent class is correctly imported
from aeiva.util.file_utils import from_json_or_yaml

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    config_path = 'agent_config.yaml'  # or 'agent_config.json'
    config = from_json_or_yaml(config_path)
    try:
        agent = Agent(config)
        agent.setup()
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logger.info("Agent execution interrupted by user.")
    except Exception as e:
        logger.error(f"An error occurred during agent execution: {e}")
    finally:
        # Perform any necessary cleanup
        try:
            agent.cognition_components['memory'].delete_all()
            logger.info("All memory units deleted during cleanup.")
        except NotImplementedError as nie:
            logger.warning(f"Delete All feature not implemented: {nie}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            print("Failed to delete all memory units.")

if __name__ == "__main__":
    main()