# memory_palace.py

import logging
import json
from typing import Any, Dict, List, Optional
from dataclasses import asdict

from aeiva.cognition.memory.memory import Memory
from aeiva.cognition.memory.memory_config import MemoryConfig
from aeiva.cognition.memory.memory_unit import MemoryUnit
from aeiva.cognition.memory.memory_utils import (
    extract_entities_relationships,
    derive_content
)
from aeiva.embedding.embedder_config import EmbedderConfig
from aeiva.embedding.embedder import Embedder
from aeiva.cognition.memory.memory_storage import MemoryStorage

logger = logging.getLogger(__name__)


class MemoryPalace(Memory):
    """
    Concrete implementation of the Memory abstract base class.

    This class provides methods to manage memory units, including creation, retrieval,
    updating, deletion, filtering, grouping, and more. It delegates all storage-related
    operations to the MemoryStorage class.
    """

    def __init__(self, config: MemoryConfig):
        """
        Initialize the MemoryPalace with the provided configuration.

        Args:
            config (MemoryConfig): Configuration settings for the MemoryPalace.
        """
        self.config = config
        self.storage = None
        self.embedder = None
        self.setup()

    def setup(self):
        """
        Setup the memory palace.
        """
        # Initializes the storage
        self.storage = MemoryStorage(self.config)

        # Initializes the embedding model based on the configuration.
        embedder_config = EmbedderConfig(
            provider_name=self.config.embedder_config.provider_name,
            model_name=self.config.embedder_config.model_name,
            api_key=self.config.embedder_config.api_key  # Replace with your actual API key
        )
        self.embedder = Embedder(embedder_config)
        logger.info("Memory palace setup successfully.")

    def create(self, content: Any, **kwargs) -> MemoryUnit:
        """
        Creates a new memory unit with the given content and metadata.

        Args:
            content (Any): The core content of the memory unit.
            **kwargs: Additional metadata for the memory unit.

        Returns:
            MemoryUnit: The created memory unit.
        """
        try:
            # Instantiate MemoryUnit
            memory_unit = MemoryUnit(content=content, **kwargs)

            # Generate embedding
            embedding_response = self.embedder.embed(content)
            if embedding_response.data:
                memory_unit.embedding = embedding_response.data[0].get("embedding")
            else:
                raise ValueError("Failed to generate embedding for the content.")

            # Delegate storage operations to MemoryStorage
            self.storage.add_memory_unit(memory_unit)

            logger.info(f"Created new MemoryUnit with ID: {memory_unit.id}")
            return memory_unit
        except Exception as e:
            logger.error(f"Error creating MemoryUnit: {e}")
            self.handle_error(e)
            raise

    def get(self, unit_id: str) -> MemoryUnit:
        """
        Retrieves a memory unit by its unique identifier.

        Args:
            unit_id (str): The unique identifier of the memory unit.

        Returns:
            MemoryUnit: The retrieved memory unit.
        """
        try:
            memory_unit = self.storage.get_memory_unit(unit_id)
            logger.info(f"Retrieved MemoryUnit with ID: {unit_id}")
            return memory_unit
        except Exception as e:
            logger.error(f"Error retrieving MemoryUnit with ID {unit_id}: {e}")
            self.handle_error(e)
            raise

    def update(self, unit_id: str, updates: Dict[str, Any]) -> None:
        """
        Updates a memory unit with the given updates.

        Args:
            unit_id (str): The unique identifier of the memory unit.
            updates (Dict[str, Any]): A dictionary of fields to update.
        """
        try:
            # If 'content' is being updated, regenerate embedding
            if 'content' in updates:
                embedding_response = self.embedder.embed(updates['content'])
                if embedding_response.data:
                    updates['embedding'] = embedding_response.data[0].get("embedding")
                    logger.info(f"Regenerated embedding for MemoryUnit ID: {unit_id}")
                else:
                    raise ValueError("Failed to generate embedding for the updated content.")

            # Delegate update operations to MemoryStorage with unit_id and updates
            self.storage.update_memory_unit(unit_id, updates)

            logger.info(f"Updated MemoryUnit with ID: {unit_id}")
        except Exception as e:
            logger.error(f"Error updating MemoryUnit with ID {unit_id}: {e}")
            self.handle_error(e)
            raise

    def delete(self, unit_id: str) -> None:
        """
        Deletes a memory unit by its unique identifier.

        Args:
            unit_id (str): The unique identifier of the memory unit.
        """
        try:
            # Delegate deletion to MemoryStorage
            self.storage.delete_memory_unit(unit_id)
            logger.info(f"Deleted MemoryUnit with ID: {unit_id}")
        except Exception as e:
            logger.error(f"Error deleting MemoryUnit with ID {unit_id}: {e}")
            self.handle_error(e)
            raise

    def get_all(self) -> List[MemoryUnit]:
        """
        Retrieves all memory units.

        Returns:
            List[MemoryUnit]: A list of all memory units.
        """
        try:
            memory_units = self.storage.get_all_memory_units()
            logger.info(f"Retrieved all MemoryUnits. Total count: {len(memory_units)}")
            return memory_units
        except Exception as e:
            logger.error(f"Error retrieving all MemoryUnits: {e}")
            self.handle_error(e)
            raise

    def delete_all(self) -> None:
        """
        Deletes all memory units.
        """
        try:
            self.storage.delete_all_memory_units()
            logger.info("Deleted all MemoryUnits.")
        except Exception as e:
            logger.error(f"Error deleting all MemoryUnits: {e}")
            self.handle_error(e)
            raise

    def load(self) -> List[MemoryUnit]:
        """
        Loads all memory units from the storage.

        Returns:
            List[MemoryUnit]: A list of all loaded memory units.
        """
        try:
            # Retrieve all memory units from storage
            memory_units = self.get_all()
            logger.info(f"Loaded {len(memory_units)} MemoryUnits from storage.")
            return memory_units
        except Exception as e:
            logger.error(f"Error loading MemoryUnits: {e}")
            self.handle_error(e)
            raise
    
    def save(self, export_path: Optional[str] = None) -> None:
        """
        Saves all memory units to the storage or exports them to a specified path.

        Args:
            export_path (Optional[str]): The file path to export memory units as JSON.
                                        If None, saves are handled by MemoryStorage.
        """
        try:
            if export_path:
                # Export memory units to a JSON file
                memory_units = self.get_all()
                export_data = [mu.to_dict() for mu in memory_units]
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=4)
                logger.info(f"Exported {len(memory_units)} MemoryUnits to {export_path}.")
            else:
                # If no export path is provided, assume that MemoryStorage handles persistence
                # This block can be used to trigger any necessary save operations in MemoryStorage
                logger.info("Save operation delegated to MemoryStorage.")
                # Example: self.storage.persist_changes()
        except Exception as e:
            logger.error(f"Error saving MemoryUnits: {e}")
            self.handle_error(e)
            raise

    def filter(self, criteria: Dict[str, Any]) -> List[MemoryUnit]:
        """
        Filters memory units based on the given criteria.

        Args:
            criteria (Dict[str, Any]): A dictionary of filter conditions.

        Returns:
            List[MemoryUnit]: A list of memory units matching the criteria.
        """
        raise NotImplementedError("Filter method is not implemented yet.")

    def group(self, unit_ids: List[str], group_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Groups memory units into a meaningful group.

        Args:
            unit_ids (List[str]): A list of memory unit IDs to group.
            group_type (str): The type of group (e.g., 'dialogue_session', 'procedure').
            metadata (Optional[Dict[str, Any]]): Additional metadata for the group.

        Returns:
            str: A unique identifier for the created group.
        """
        raise NotImplementedError("Group method is not implemented yet.")

    def derive(self, unit_ids: List[str], derivation_type: str, **kwargs) -> MemoryUnit:
        """
        Derives a new memory unit from existing ones.

        Args:
            unit_ids (List[str]): A list of memory unit IDs to derive from.
            derivation_type (str): The type of derivation (e.g., 'summary', 'transformation').
            **kwargs: Additional parameters for the derivation process.

        Returns:
            MemoryUnit: The derived memory unit.
        """
        try:
            # Retrieve the content of the specified memory units
            contents = [self.get(unit_id).content for unit_id in unit_ids]
            combined_content = ' '.join(contents)

            # Use lmp functions to derive new content
            derived_content = derive_content(derivation_type, combined_content)

            # Create a new MemoryUnit with the derived content
            derived_unit = self.create(
                content=derived_content,
                type=derivation_type,
                source_role="derived",
                metadata=kwargs.get('metadata')
            )

            logger.info(f"Derived new memory unit with ID: {derived_unit.id}")
            return derived_unit
        except Exception as e:
            logger.error(f"Error deriving memory unit: {e}")
            self.handle_error(e)
            raise

    def structurize(self, unit_ids: List[str], structure_type: str, **kwargs) -> None:
        """
        Structures memory units into a knowledge graph or other structures.

        Args:
            unit_ids (List[str]): A list of memory unit IDs to structurize.
            structure_type (str): The type of structure (e.g., 'knowledge_graph').
            **kwargs: Additional parameters for the structuring process.
        """
        raise NotImplementedError("Structurize method is not implemented yet.")

    def skillize(self, unit_ids: List[str], skill_name: str, **kwargs) -> str:
        """
        Converts memory units into a reusable skill.

        Args:
            unit_ids (List[str]): A list of memory unit IDs to skillize.
            skill_name (str): The name of the skill to create.
            **kwargs: Additional parameters for skill creation.

        Returns:
            str: The unique identifier of the created skill.
        """
        raise NotImplementedError("Skillize method is not implemented yet.")

    def embed(self, unit_id: str) -> None:
        """
        Generates an embedding for a memory unit.

        Args:
            unit_id (str): The unique identifier of the memory unit.
        """
        try:
            # Retrieve the memory unit
            memory_unit = self.get(unit_id)
            if not memory_unit:
                raise ValueError(f"MemoryUnit with ID {unit_id} does not exist.")

            # Generate embedding using the embedder
            embedding_response = self.embedder.embed(memory_unit.content)
            if embedding_response.data and len(embedding_response.data) > 0:
                memory_unit.embedding = embedding_response.data[0].get("embedding")
            else:
                raise ValueError("Failed to generate embedding for the content.")

            # Update the memory unit with the new embedding
            self.update(unit_id, {'embedding': memory_unit.embedding})

            logger.info(f"Generated embedding for MemoryUnit ID: {unit_id}")
        except Exception as e:
            logger.error(f"Error generating embedding for MemoryUnit ID {unit_id}: {e}")
            self.handle_error(e)
            raise

    def parameterize(self, **kwargs) -> None:
        """
        Trains a parametric model using the memory data.

        Args:
            **kwargs: Additional parameters for the training process.
        """
        raise NotImplementedError("Parameterize method is not implemented yet.")

    def retrieve(self, query: Any, retrieve_type: str, **kwargs) -> List[MemoryUnit]:
        """
        Retrieve data from memory based on a query.

        Args:
            query (Any): The query or criteria to retrieve specific memory data.
            retrieve_type (str): The type of retrieval (e.g., 'retrieve_related', 'retrieve_similar').
            **kwargs: Additional parameters for the retrieval process.

        Returns:
            List[MemoryUnit]: The retrieved memory data.
        """
        try:
            if retrieve_type == 'retrieve_similar':
                return self.retrieve_similar(query, **kwargs)
            elif retrieve_type == 'retrieve_related':
                return self.retrieve_related(query, **kwargs)
            else:
                raise ValueError(f"Unknown retrieve_type: {retrieve_type}")
        except Exception as e:
            logger.error(f"Error retrieving MemoryUnits: {e}")
            self.handle_error(e)
            raise

    def retrieve_similar(self, query: Any, top_k: int = 5) -> List[MemoryUnit]:
        """
        Retrieves memory units similar to the given input based on embeddings.

        Args:
            query (Any): The query for retrieval.
            top_k (int): The number of similar units to retrieve.

        Returns:
            List[MemoryUnit]: A list of similar memory units.
        """
        try:
            # Generate embedding for the query
            embedding_response = self.embedder.embed(query)
            if not embedding_response.data:
                raise ValueError("Failed to generate embedding for the query.")

            query_embedding = embedding_response.data[0].get("embedding")

            # Perform similarity search via MemoryStorage
            similar_units = self.storage.retrieve_similar_memory_units(query_embedding, top_k)
            logger.info(f"Retrieved {len(similar_units)} similar MemoryUnits.")
            return similar_units
        except Exception as e:
            logger.error(f"Error retrieving similar MemoryUnits: {e}")
            self.handle_error(e)
            raise

    def retrieve_related(self, query: Any, relationship: Optional[str] = None) -> List[MemoryUnit]:
        """
        Retrieves memory units related to the given one based on relationships.

        Args:
            query (Any): The query for retrieval.
            relationship (Optional[str]): Filter by relationship type.

        Returns:
            List[MemoryUnit]: A list of related memory units.
        """
        try:
            # Assuming 'query' is a memory unit ID
            memory_unit = self.get(query)

            # Perform related retrieval via MemoryStorage
            related_units = self.storage.retrieve_related_memory_units(memory_unit.id, relationship)
            logger.info(f"Retrieved {len(related_units)} related MemoryUnits.")
            return related_units
        except Exception as e:
            logger.error(f"Error retrieving related MemoryUnits: {e}")
            self.handle_error(e)
            raise

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur during memory operations.

        Args:
            error (Exception): The exception that was raised.
        """
        logger.error(f"MemoryPalace encountered an error: {error}")
        # Additional error handling can be implemented here