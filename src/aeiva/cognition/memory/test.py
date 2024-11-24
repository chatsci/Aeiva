# test_memory_palace.py

import logging
import os
from aeiva.cognition.memory.memory_palace import MemoryPalace
from aeiva.cognition.memory.memory_config import MemoryConfig
from aeiva.embedding.embedder_config import EmbedderConfig
from aeiva.storage.database_factory import DatabaseConfigFactory
from dotenv import load_dotenv


# Load environment variables (API keys, etc.)
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_default_api_key_here")

# Ensure 'storage' directory exists
os.makedirs('storage', exist_ok=True)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# embedder_dimensions.py

MODEL_EMBEDDING_DIMENSIONS = {
    'text-embedding-ada-002': 1536,
    # Add other models and their embedding dimensions as needed
}


def main():
    # Embedder Configuration
    embedder_config = EmbedderConfig(
        provider_name='openai',
        model_name='text-embedding-ada-002',
        api_key=OPENAI_API_KEY,  # Replace with your actual OpenAI API key
    )

    # Vector Database Configuration (Milvus)
    vector_db_config = DatabaseConfigFactory.create(
        provider_name='milvus',
        uri='storage/milvus_demo.db',
        collection_name='test_collection',
        embedding_model_dims=MODEL_EMBEDDING_DIMENSIONS.get(embedder_config.model_name),  # 1536
        metric_type='COSINE',
    )

    # Graph Database Configuration (Neo4j)
    graph_db_config = DatabaseConfigFactory.create(
        provider_name='neo4j',
        uri='bolt://localhost:7687',
        user='neo4j',
        password='cf57bwP9pcdcEK3',  # Replace with your actual password
        database='neo4j',
        encrypted=False,
    )

    # Relational Database Configuration (SQLite)
    relational_db_config = DatabaseConfigFactory.create(
        provider_name='sqlite',
        database='storage/test_database.db'  # Use a file-based database for persistence
    )

    # Memory Configuration
    memory_config = MemoryConfig(
        embedder_config=embedder_config,
        vector_db_provider='milvus',
        vector_db_config=vector_db_config,
        graph_db_provider='neo4j',
        graph_db_config=graph_db_config,
        relational_db_provider='sqlite',
        relational_db_config=relational_db_config,
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
        print(f"Created MemoryUnit with id and content: {memory_unit.id} {memory_unit.content}")

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
        print(f"Updated MemoryUnit with id and content: {updated_unit.id} {updated_unit.content}")

        # Retrieve similar memory units using the generalized 'retrieve' method
        similar_units = memory_palace.retrieve(
            query="Explain the concept of MemoryPalace in programming.",
            retrieve_type="similar",
            top_k=5
        )
        print(f"Retrieved {len(similar_units)} similar MemoryUnits.")
        for mu in similar_units:
            print(mu)

        # Organize (group) MemoryUnits into a dialogue session
        organize_id = memory_palace.organize(
            unit_ids=[memory_unit.id],
            organize_type="dialogue_session",
            metadata={"session_topic": "Graph Databases"}
        )
        print(f"Created Dialogue Group with ID: {organize_id}")

        # Structurize MemoryUnits into a knowledge graph
        try:
            memory_palace.structurize(
                unit_ids=[memory_unit.id],
                structure_type="knowledge_graph"
            )
            print(f"Structurized MemoryUnit with ID: {memory_unit.id} into knowledge graph.")
        except NotImplementedError as nie:
            logger.warning(f"Structurize feature not implemented: {nie}")

        # Skillize MemoryUnits into a reusable skill
        try:
            skill_id = memory_palace.skillize(
                unit_ids=[memory_unit.id],
                skill_name="GraphDatabaseTutorial"
            )
            print(f"Created Skill with ID: {skill_id}")
        except NotImplementedError as nie:
            logger.warning(f"Skillize feature not implemented: {nie}")

        # Parameterize Memories (e.g., train a model)
        try:
            memory_palace.parameterize(
                training_epochs=10  # Example parameter, adjust as needed
            )
            print("Parameterized memories successfully.")
        except NotImplementedError as nie:
            logger.warning(f"Parameterize feature not implemented: {nie}")

        # Embed a memory unit (optional, since embedding is done during creation)
        try:
            memory_palace.embed(memory_unit.id)
            print(f"Generated embedding for MemoryUnit ID: {memory_unit.id}")
        except NotImplementedError as nie:
            logger.warning(f"Embed feature not implemented: {nie}")

        # Delete the memory unit
        memory_palace.delete(memory_unit.id)
        print(f"Deleted MemoryUnit with ID: {memory_unit.id}")

        # Retrieve all memory units
        all_units = memory_palace.get_all()
        print(f"Total MemoryUnits after deletion: {len(all_units)}")

    except NotImplementedError as nie:
        logger.warning(f"Feature not implemented: {nie}")
    except Exception as e:
        logger.error(f"An error occurred during testing: {e}")

    finally:
        # Clean up resources if necessary
        try:
            memory_palace.delete_all()
            print("All memory units deleted.")
        except NotImplementedError as nie:
            logger.warning(f"Delete All feature not implemented: {nie}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            print("Failed to delete all memory units.")


if __name__ == '__main__':
    main()