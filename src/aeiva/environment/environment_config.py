# environment_config.py

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from aeiva.config.base_config import BaseConfig

@dataclass
class EnvironmentConfig(BaseConfig):
    """
    Configuration class for initializing an environment.
    
    Attributes:
        environment_type (str): Type of the environment, see EnvironmentType class.
        initial_state (Optional[Any]): Optional initial state of the environment.
        constraints (Dict[str, Any]): Rules or constraints governing the environment.
        entities (List[Any]): Entities present within the environment.
        time_enabled (bool): Whether the environment tracks time progression.
    """

    environment_type: str = field(
        metadata={"help": "Type of the environment (e.g., 'user', 'document', 'game')."}
    )
    initial_state: Optional[Any] = field(
        default=None,
        metadata={"help": "Optional initial state of the environment."}
    )
    constraints: Dict[str, Any] = field(
        default_factory=dict,
        metadata={"help": "Rules or constraints for the environment."}
    )
    entities: List[Any] = field(
        default_factory=list,
        metadata={"help": "Entities within the environment."}
    )
    time_enabled: bool = field(
        default=False,
        metadata={"help": "Flag to enable time progression."}
    )

    def __post_init__(self):
        super().__post_init__()
        # Perform any necessary validation
        if not self.environment_type:
            raise ValueError("Environment type must be provided.")
        # Further validation checks can be added here if needed