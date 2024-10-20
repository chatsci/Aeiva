import asyncio
from pprint import pprint
from aeiva.agent.toy_agent.environment import ToyEnvironment, ToyEnvironmentError

async def main():
    # Define the configuration for the ToyEnvironment
    config = {
        "grid_size": (5, 5),  # You can add any additional configuration here if needed
    }
    
    # Instantiate the ToyEnvironment
    env = ToyEnvironment(config)
    
    # Set up the Environment
    try:
        await env.setup()
    except ToyEnvironmentError as e:
        print(f"Setup Error: {e}")
        return
    
    # Define a list of actions (external inputs) to update the environment
    actions = [
        {"move": "right"},
        {"move": "down"},
        {"move": "left"},
        {"move": "up"},
        {"move": "down"},
        {"move": "right"},
    ]
    
    # Process each action one by one in a cycle
    for action in actions:
        print(f"\nTest: Applying action -> {action}")
        try:
            # Update the environment with the action
            await env.update(action)
            
            # Get the current observation from the environment (agent's position on the grid)
            observation = env.get_observation()
            print("Environment: Observation (Agent's Position) ->")
            pprint(observation)  # Pretty print the observation
            
        except ToyEnvironmentError as e:
            print(f"Run Error: {e}")

    # Reset the environment after all actions have been processed
    print("\nResetting the environment to its initial state...")
    await env.reset()

    # Get the observation after the reset
    observation = env.get_observation()
    print("Environment: Observation after reset ->")
    pprint(observation)  # Pretty print the observation

# Entry point for the test script
if __name__ == "__main__":
    asyncio.run(main())