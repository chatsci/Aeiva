import asyncio
from aeiva.agent.toy_agent.agent import ToyAgent, AgentError

async def main():
    # Define the configuration for the ToyAgent
    config = {
        "cognition": {
            "brain": {},
            "memory": {},
            "world_model": {},
            "emotion": {}
        },
        "action_system": {},
        "perception": {}
    }
    
    # Instantiate the ToyAgent
    agent = ToyAgent(config)
    
    # Set up the Agent
    try:
        await agent.setup()
    except AgentError as e:
        print(f"Setup Error: {e}")
        return
    
    # Define a list of stimuli to process
    stimuli_list = [
        {"type": "message", "content": "Hello, agent!"},
        {"type": "request", "content": "I need assistance."},
        {"type": "request", "content": "Tell me a joke."},
        {"type": "farewell", "content": "Goodbye!"}
    ]
    
    # Process each stimulus one by one in a cycle
    for stimuli in stimuli_list:
        print(f"\nTest: Sending stimuli -> {stimuli['content']}")
        try:
            await agent.perception_system.perceive(stimuli)
            observations = agent.perception_system.get_observations()
            print(f"Agent: Observations -> {observations}")

            # Assuming the correct method in ToyCognitionSystem is process_observation or decide_actions
            cognitive_response = await agent.cognition_system.process_observation(observations)  # Replace with correct method
            print(f"Agent: Cognitive Response -> {cognitive_response}")

            action = {"action_type": "respond", "parameters": {"message": cognitive_response}}
            await agent.action_system.execute(action)
            print(f"Agent: Action executed -> {action}")
        except AgentError as e:
            print(f"Run Error: {e}")

# Entry point for the test script
if __name__ == "__main__":
    asyncio.run(main())