# Example test
if __name__ == "__main__":
    import asyncio
    from aeiva.cognition.brain.llm_brain import LLMBrain
    from aeiva.cognition.input_interpreter.llm_input_interpreter import LLMInputInterpreter
    from aeiva.cognition.output_orchestrator.llm_output_orchestrator import LLMOutputOrchestrator
    from aeiva.cognition.memory.simple_memory import SimpleMemory
    from aeiva.cognition.emotion.simple_emotion import SimpleEmotion
    from aeiva.cognition.world_model.simple_world_model import SimpleWorldModel
    from aeiva.llm.llm_gateway_config import LLMGatewayConfig
    from dotenv import load_dotenv
    import os

    # Load environment variables from .env
    load_dotenv()

    # Fetch the API key from environment variables
    API_KEY = os.getenv('OPENAI_API_KEY')

    async def test_cognition_system():
        # Initialize all components for the cognition system
        config = LLMGatewayConfig(
            llm_api_key=API_KEY,
            llm_model_name="gpt-3.5-turbo",
            llm_temperature=0.7,
            llm_max_output_tokens=100,
            llm_logging_level="info",
            llm_stream=False
        )

        input_interpreter = LLMInputInterpreter()
        brain = LLMBrain(config)
        output_orchestrator = LLMOutputOrchestrator()
        memory = SimpleMemory()
        emotion = SimpleEmotion()
        world_model = SimpleWorldModel()

        # Initialize cognition system
        cognition_system = SimpleCognitionSystem(
            input_interpreter=input_interpreter,
            brain=brain,
            output_orchestrator=output_orchestrator,
            memory=memory,
            emotion=emotion,
            world_model=world_model
        )

        # Set up the system
        await cognition_system.setup()

        # Define some input (observation)
        observation = {
            "role": "user",
            "content": "First, Do you know what is large language model? Second, can you calculate 9 test operation 10 based on tools?"
        }

        # Run the cognition system
        action_plan = await cognition_system.run(observation)
        print(f"Action Plan: {action_plan}")

    # Run the test
    asyncio.run(test_cognition_system())