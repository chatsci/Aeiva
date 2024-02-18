from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Union, Optional, Tuple
from collections import deque


class AgentBase(ABC):
    def __init__(self, 
                 id: str, 
                 name: str, 
                 perception_system: PerceptionSystem, 
                 cognitive_system: CognitiveSystem, 
                 action_system: ActionSystem,
                 role: Optional[Role] = None,
                 background: Optional[Background] = None,
                 relationships: Optional[Dict[str, Relationship]] = None,
                 *args,
                 **kwargs):
        self.id = id
        self.name = name
        self.perception_system = perception_system
        self.cognitive_system = cognitive_system
        self.action_system = action_system
        self.memory = {}
        self.world_model = None
        self.goal = None
        self.role = role
        self.background = background
        self.relationships = relationships if relationships else {}

    @abstractmethod
    def perceive(self, stimuli: Stimuli, *args, **kwargs):
        """
        The agent takes in stimuli from the environment and processes it,
        the result is then passed to the cognitive system for further processing.
        """
        processed_data = self.perception_system.process(stimuli)
        self.memory['last_perception'] = processed_data
        return processed_data

    @abstractmethod
    def think(self, *args, **kwargs):
        """
        The agent uses its cognitive system to plan actions based on the current state
        of the world and its goals. It also uses its memory and potentially updates its world model.
        """
        cognitive_output = self.cognitive_system.process(self.memory)
        self.memory['last_cognition'] = cognitive_output
        return cognitive_output

    @abstractmethod
    def act(self, *args, **kwargs):
        """
        The agent performs an action in the environment using its action system,
        this action is based on the output from the cognitive system.
        """
        action = self.cognitive_system.get_last_action()
        self.action_system.perform(action)

    @abstractmethod
    def learn(self, *args, **kwargs):
        """
        The agent updates its perception, cognition, and action systems based on the feedback it gets from the environment,
        this could be done using various machine learning techniques.
        """
        pass

    @abstractmethod
    def set_goal(self, goal: Any, *args, **kwargs):
        """
        The agent sets its goal, which could guide its cognitive system in making decisions.
        """
        self.goal = goal

    @abstractmethod
    def update_world_model(self, world_model: WorldModel, *args, **kwargs):
        """
        The agent updates its world model, which could be used in the cognitive system for making decisions.
        """
        self.world_model = world_model

    @abstractmethod
    def set_role(self, role: Role):
        """
        The agent sets its role in the society, which could guide its actions and interactions with other agents.
        """
        self.role = role

    @abstractmethod
    def set_background(self, background: Background):
        """
        The agent sets its background, which could influence its behavior and interactions with other agents.
        """
        self.background = background

    @abstractmethod
    def add_relationship(self, other_agent_id: str, relationship: Relationship):
        """
        The agent adds a relationship with another agent, which could influence its behavior and interactions with the other agent.
        """
        self.relationships[other_agent_id] = relationship

    @abstractmethod
    def remove_relationship(self, other_agent_id: str):
        """
        The agent removes a relationship with another agent.
        """
        if other_agent_id in self.relationships:
            del self.relationships[other_agent_id]
