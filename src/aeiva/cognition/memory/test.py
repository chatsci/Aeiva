# test_memory_palace.py

import logging
from aeiva.cognition.memory.memory_palace import MemoryPalace
from aeiva.configs.memory_config import MemoryConfig
from aeiva.configs.embedder_config import EmbedderConfig
from aeiva.configs.llm_config import LLMConfig
from aeiva.storage.database_config import DatabaseConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    # Create configurations for the components

    # Embedder Configuration
    embedder_config = EmbedderConfig(
        provider_name='openai',
        model_name='text-embedding-ada-002',
        api_key='your_openai_api_key',  # Replace with your actual OpenAI API key
    )

    # Vector Database Configuration (Milvus)
    vector_db_config = DatabaseConfig(
        provider_name='milvus',
        host='localhost',
        port=19530,
        collection_name='memory_units',
        embedding_model_dims=1536,
    )

    # Graph Database Configuration (Neo4j)
    graph_db_config = DatabaseConfig(
        provider_name='neo4j',
        uri='bolt://localhost:7687',
        user='neo4j',
        password='your_neo4j_password',  # Replace with your actual Neo4j password
        database='neo4j',
    )

    # Relational Database Configuration (SQLite)
    relational_db_config = DatabaseConfig(
        provider_name='sqlite',
        database='memory_events.db'  # Path to the SQLite database file
    )

    # LLM Configuration
    llm_config = LLMConfig(
        provider_name='openai',
        model_name='gpt-3.5-turbo',
        api_key='your_openai_api_key',  # Replace with your actual OpenAI API key
    )

    # Memory Configuration
    memory_config = MemoryConfig(
        embedder_config=embedder_config,
        vector_db_config=vector_db_config,
        graph_db_config=graph_db_config,
        relational_db_config=relational_db_config,
        llm_config=llm_config,
    )

    # Initialize MemoryPalace
    memory_palace = MemoryPalace(config=memory_config)

    try:
        # Create a new memory unit
        memory_unit = memory_palace.create(
            content="Today I learned about the MemoryPalace implementation in Python.",
            modality='text',
            type='note',
            tags=['learning', 'python', 'memory'],
            source_role='user',
            source_name='TestUser',
        )
        print(f"Created MemoryUnit: {memory_unit}")

        # Retrieve the memory unit
        retrieved_unit = memory_palace.get(memory_unit.id)
        print(f"Retrieved MemoryUnit: {retrieved_unit}")

        # Update the memory unit
        memory_palace.update(
            unit_id=memory_unit.id,
            updates={'tags': ['learning', 'python', 'memory', 'update_test']}
        )
        print(f"Updated MemoryUnit tags.")

        # Retrieve the updated memory unit
        updated_unit = memory_palace.get(memory_unit.id)
        print(f"Updated MemoryUnit: {updated_unit}")

        # Retrieve similar memory units
        similar_units = memory_palace.retrieve_similar(
            query="Explain the concept of MemoryPalace in programming.",
            top_k=5
        )
        print(f"Retrieved {len(similar_units)} similar MemoryUnits.")

        # Delete the memory unit
        memory_palace.delete(memory_unit.id)
        print(f"Deleted MemoryUnit with ID: {memory_unit.id}")

        # Retrieve all memory units
        all_units = memory_palace.get_all()
        print(f"Total MemoryUnits after deletion: {len(all_units)}")

    except Exception as e:
        logger.error(f"An error occurred during testing: {e}")

    finally:
        # Clean up resources if necessary
        memory_palace.delete_all()
        print("All memory units deleted.")


if __name__ == '__main__':
    main()