from aeiva.environment.environment import Environment
from typing import Any
import asyncio


class ToyEnvironmentError(Exception):
    """Exception raised for errors in the ToyEnvironment system."""
    pass


class ToyEnvironment(Environment):
    """
    A toy implementation of the Environment class, representing a simple grid world.
    """
    
    def init_state(self) -> Any:
        """
        Initialize a simple grid state with an agent starting at position (0, 0).
        """
        return {
            "grid": [[0 for _ in range(5)] for _ in range(5)],
            "agent_position": (0, 0)
        }

    async def setup(self) -> None:
        """
        Set up the environment (in this case, no additional setup is needed).
        """
        await asyncio.sleep(0.1)  # Simulate a setup delay
        print("ToyEnvironment setup completed.")

    async def reset(self) -> None:
        """
        Reset the environment to the initial state.
        """
        self.state = self.init_state()
        print("ToyEnvironment has been reset.")

    async def update(self, external_input: Any) -> None:
        """
        Update the environment based on external input, which could be a movement command.
        """
        try:
            direction = external_input.get("move")
            if direction == "up":
                self._move_agent(0, -1)
            elif direction == "down":
                self._move_agent(0, 1)
            elif direction == "left":
                self._move_agent(-1, 0)
            elif direction == "right":
                self._move_agent(1, 0)
        except Exception as e:
            self.handle_error(e)
            raise ToyEnvironmentError("Failed to update environment.") from e

    def get_observation(self) -> Any:
        """
        Return the current observation, which is the agent's position on the grid.
        """
        return self.state["agent_position"]

    def _move_agent(self, dx: int, dy: int) -> None:
        """
        Internal method to move the agent on the grid.
        """
        x, y = self.state["agent_position"]
        new_x, new_y = x + dx, y + dy
        if 0 <= new_x < 5 and 0 <= new_y < 5:
            self.state["agent_position"] = (new_x, new_y)
            print(f"Agent moved to position: {self.state['agent_position']}")
        else:
            print("Move out of bounds. Agent stays in place.")