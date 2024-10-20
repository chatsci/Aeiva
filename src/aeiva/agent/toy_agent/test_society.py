import asyncio
from aeiva.agent.toy_agent.environment import ToyEnvironment  # Use the defined ToyEnvironment
from aeiva.agent.toy_agent.agent import ToyAgent  # Use the defined ToyAgent
from aeiva.agent.toy_agent.society import ToySociety

async def main():
    # Configuration for the ToySociety
    config = {
        "society_name": "TestSociety",
        "cycle_interval": 1.0
    }

    # Create the environment
    env = ToyEnvironment(config)

    # Create agents
    agents = {
        "agent_1": ToyAgent({"id": "agent_1"}),
        "agent_2": ToyAgent({"id": "agent_2"})
    }

    # Instantiate the ToySociety
    society = ToySociety(config, env, agents)

    # Set up the society
    await society.setup()

    # Run the society for a few cycles
    print("\nRunning ToySociety for 3 cycles...")
    try:
        await asyncio.wait_for(society.run(), timeout=3.5)
    except asyncio.TimeoutError:
        print("\nSociety run terminated after 3 cycles.")

    # Print the communication log
    print("\nCommunication Log:")
    for log in society.get_communication_log():
        print(log)

if __name__ == "__main__":
    asyncio.run(main())