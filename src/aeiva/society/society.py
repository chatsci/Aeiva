from abc import ABC, abstractmethod
from typing import Any, List, Dict
import asyncio


class Society(ABC):
    """
    Abstract base class representing a Society that connects an environment and agents.

    The Society enables agents to interact with each other and with the environment, providing
    mechanisms for integrating social systems, such as communication or economy.

    Attributes:
        config (Any): Configuration settings for the society.
        environment (Environment): The environment in which agents operate.
        agents (Dict[str, Any]): A dictionary of agents within the society.
        social_systems (Dict[str, Any]): A dictionary representing various social systems (e.g., communication).
    """

    def __init__(self, config: Any, environment: Any, agents: Dict[str, Any]):
        """
        Initialize the Society with the provided configuration, environment, and agents.

        Args:
            config (Any): Configuration settings for the society.
            env (Environment): The environment in which agents operate.
            agents (Dict[str, Any]): A dictionary of agents within the society, keyed by their IDs.
        """
        self.config = config
        self.environment = environment
        self.agents = agents  # Agents are stored in a dictionary with IDs as keys
        self.social_systems = self.init_social_systems()

    @abstractmethod
    def init_social_systems(self) -> Dict[str, Any]:
        """
        Initialize the social systems that operate within the society (e.g., communication, financial, law, political, social network systems).

        Returns:
            Dict[str, Any]: A dictionary of initialized social systems.
        """
        pass

    @abstractmethod
    async def setup(self) -> None:
        """
        Asynchronously set up the society's components, such as initializing the environment and agents.
        """
        await self.env.setup()
        await asyncio.gather(*(agent.setup() for agent in self.agents.values()))
        print("Society: Setup completed.")

    @abstractmethod
    async def run(self) -> None:
        """
        Asynchronously run the society, managing interactions between agents and the environment.

        This method should control the flow of interactions between agents and the environment,
        and it can be designed as a continuous loop or a task-based execution.
        """
        pass

    def add_agent(self, agent_id: str, agent: Any) -> None:
        """
        Add a new agent to the society.

        Args:
            agent_id (str): The unique identifier of the agent.
            agent (Any): The agent object to add to the society.
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

    def get_agent(self, agent_id: str) -> Any:
        """
        Retrieve an agent by its ID.

        Args:
            agent_id (str): The unique identifier of the agent.

        Returns:
            Any: The agent object, if found.
        """
        return self.agents.get(agent_id, None)

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur during society operations.

        Args:
            error (Exception): The exception that was raised.
        """
        print(f"Society encountered an error: {error}")