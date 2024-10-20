from typing import Any, Dict
from aeiva.agent.toy_agent.environment import ToyEnvironment  # Use the defined ToyEnvironment
from aeiva.agent.toy_agent.agent import ToyAgent  # Use the defined ToyAgent
import asyncio

class ToySociety:
    """
    A simple society that manages an environment and a set of agents, with basic social systems.
    """
    
    def __init__(self, config: Any, environment: ToyEnvironment, agents: Dict[str, ToyAgent]):
        """
        Initialize the ToySociety with a configuration, environment, and agents.

        Args:
            config (Any): Configuration settings for the society.
            environment (ToyEnvironment): The environment in which agents operate.
            agents (Dict[str, ToyAgent]): A dictionary of agents, keyed by their IDs.
        """
        self.config = config
        self.environment = environment
        self.agents = agents
        self.social_systems = self.init_social_systems()

    def init_social_systems(self) -> Dict[str, Any]:
        """
        Initialize the social systems for the society.

        This example includes a basic communication system.
        
        Returns:
            Dict[str, Any]: Initialized social systems, such as a communication system.
        """
        return {
            "communication_system": {"history": []},
        }

    async def setup(self) -> None:
        """
        Asynchronously set up the society, including the environment and agents.
        """
        await self.env.setup()
        await asyncio.gather(*(agent.setup() for agent in self.agents.values()))
        print("ToySociety: All systems set up.")

    async def run(self) -> None:
        """
        Run a simple simulation where agents interact with the environment and each other.
        """
        while True:
            for agent_id, agent in self.agents.items():
                # Each agent observes the environment
                observation = self.env.get_observation()
                print(f"Agent {agent_id} observes: {observation}")

                # Each agent takes an action based on the observation
                await agent.cycle()

                # Simulate communication in the social system
                message = f"Agent {agent_id} says: 'I see {observation}'"
                self.social_systems["communication_system"]["history"].append(message)
                print(f"Communication log: {message}")

            # Sleep for a cycle
            await asyncio.sleep(1.0)

    def get_communication_log(self) -> Any:
        """
        Get the history of communications within the society.

        Returns:
            List: Communication history.
        """
        return self.social_systems["communication_system"]["history"]

    def add_agent(self, agent_id: str, agent: ToyAgent) -> None:
        """
        Add a new agent to the society.

        Args:
            agent_id (str): The unique identifier of the agent.
            agent (ToyAgent): The agent object to add to the society.
        """
        self.agents[agent_id] = agent

    def remove_agent(self, agent_id: str) -> None:
        """
        Remove an agent from the society by its ID.

        Args:
            agent_id (str): The unique identifier of the agent.
        """
        if agent_id in self.agents:
            del self.agents[agent_id]

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur during society operations.

        Args:
            error (Exception): The exception that was raised.
        """
        print(f"Society encountered an error: {error}")