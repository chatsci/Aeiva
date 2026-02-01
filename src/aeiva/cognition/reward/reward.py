# File: cognition/reward.py

from typing import Any

from aeiva.cognition.mental_state import MentalState


class Reward(MentalState):
    """
    Tracks the agent's cumulative reward signal.
    """

    def init_state(self) -> Any:
        # Start with 0.0 reward
        return 0.0

    def setup(self) -> None:
        """
        Load an initial reward from config if present, else 0.0
        """
        initial = self.config.get("initial_reward", 0.0)
        self.state = float(initial)

    async def update(self, new_data: Any) -> None:
        """
        If new_data is numeric, add to the running total.
        """
        if isinstance(new_data, (int, float)):
            self.state += float(new_data)

    async def query(self, query_data: Any) -> Any:
        """
        - If query_data == "current_value", return the float directly.
        - Otherwise, return a dict with "cumulative_reward".
        """
        if query_data == "current_value":
            return self.state
        return {"cumulative_reward": self.state}