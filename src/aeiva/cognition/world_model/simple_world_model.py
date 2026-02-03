# File: cognition/simple_world_model.py

import logging
from typing import Any, List

from aeiva.cognition.world_model.base_world_model import WorldModel

logger = logging.getLogger(__name__)


class SimpleWorldModel(WorldModel):

    def __init__(self, config: Any = None):
        super().__init__(config)
        self.state = self.init_state()

    def init_state(self) -> List[dict]:
        return []

    def setup(self) -> None:
        logger.debug("SimpleWorldModel setup complete.")

    async def update(self, observation: dict) -> None:
        if not isinstance(observation, dict):
            raise ValueError("Observation must be a dictionary.")
        
        self.state.append(observation)
        logger.debug("World model updated with new observation: %s", observation)

    async def query(self, query: Any) -> List[dict]:
        if isinstance(query, dict) and 'keyword' in query:
            keyword = query['keyword']
            return [obs for obs in self.state if keyword in obs.get('content', '')]
        
        return self.state

    def get_current_state(self) -> List[dict]:
        return self.state
