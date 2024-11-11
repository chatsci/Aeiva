# File: cognition/simple_memory.py

from aeiva.cognition.memory.memory import Memory
from typing import Any, List


class SimpleMemory:

    def __init__(self, config: Any = None):
        # super().__init__(config)
        self.state = self.init_state()

    def init_state(self) -> List[dict]:
        return []

    def setup(self) -> None:
        print("SimpleMemory setup complete.")

    async def retrieve(self, query: Any) -> List[dict]:
        if isinstance(query, dict) and 'keyword' in query:
            keyword = query['keyword']
            return [message for message in self.state if keyword in message.get('content', '')]
        return self.state

    async def store(self, data: dict) -> None:
        if not isinstance(data, dict):
            raise ValueError("Stored data must be a dictionary.")
        
        self.state.append(data)
        print(f"Data stored in memory: {data}")

    def get_current_state(self) -> List[dict]:
        return self.state