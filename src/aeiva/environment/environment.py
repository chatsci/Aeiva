from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from aeiva.environment.environment_config import EnvironmentConfig

class Environment(ABC):
    """
    Abstract base class for an environment in which an intelligent agent operates.
    
    Each environment provides context, defines interactions, and manages its own state.
    Subclasses should implement specific methods for different types of environments.

    Attributes:
        config (EnvironmentConfig): Configuration settings for the environment.
        state (Any): Current state of the environment, initialized from the config.
        entities (List[Any]): Entities present within the environment.
        constraints (Dict[str, Any]): Rules or limitations for interactions in the environment.
        time (Optional[int]): Time progression within the environment, if enabled.
    """
    
    def __init__(self, config: EnvironmentConfig):
        """
        Initialize the environment with a given configuration.
        
        Args:
            config (EnvironmentConfig): Configuration settings for the environment.
        """
        self.config = config
        self.state = config.initial_state
        self.entities = config.entities
        self.constraints = config.constraints
        self.time = 0 if config.time_enabled else None
        self.setup()

    @abstractmethod
    def setup(self):
        """
        Set up the environment based on its configuration.
        Subclasses should define any initialization logic here.
        """
        pass

    @abstractmethod
    def reset(self):
        """
        Reset the environment to its initial state as defined by the configuration.
        """
        self.state = self.config.initial_state
        self.time = 0 if self.config.time_enabled else None

    @abstractmethod
    def step(self, actions: Dict[Any, Any]):
        """
        Advance the environment by one step based on actions taken by agents.
        
        Args:
            actions (Dict[Any, Any]): A dictionary of actions performed by agents.
        """
        pass

    @abstractmethod
    def observe(self, agent: Any) -> Any:
        """
        Provide observations to an agent based on the current state.
        
        Args:
            agent (Any): The agent requesting observation.
        
        Returns:
            Any: Observation data formatted according to the agent's perception capabilities.
        """
        pass

    @abstractmethod
    def act(self, action: Any, target: Optional[Any] = None):
        """
        Execute an action in the environment, potentially modifying its state.
        
        Args:
            action (Any): The action to be executed.
            target (Optional[Any]): Target entity for the action, if applicable.
        """
        pass

    def render(self):
        """
        Visualize or output the environment's current state. Optional for subclasses.
        """
        print(f"Environment State: {self.state}")

    def get_context(self) -> Any:
        """
        Retrieve relevant context information from the environment, useful for agent processing.
        
        Returns:
            Any: Contextual data or state relevant to the agent's tasks.
        """
        return self.state

    def close(self):
        """
        Clean up any resources tied to the environment when it's no longer needed.
        """
        print("Closing environment and releasing resources.")

    def __repr__(self) -> str:
        return (f"Environment(type={self.config.environment_type}, "
                f"state={self.state}, "
                f"entities={self.entities}, "
                f"time={self.time}, "
                f"constraints={self.constraints})")