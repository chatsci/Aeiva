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

from aeiva.cognition.memory.memory_cleaner import MemoryCleaner
from aeiva.cognition.memory.memory_organizer import MemoryOrganizer
from aeiva.cognition.memory.memory_structurer import MemoryStructurer
from aeiva.cognition.memory.memory_retriever import MemoryRetriever
from aeiva.cognition.memory.memory_skillizer import MemorySkillizer
from aeiva.cognition.memory.memory_parameterizer import MemoryParameterizer

from aeiva.storage.database_factory import DatabaseConfigFactory

logger = logging.getLogger(__name__)


class MemoryPalace(Memory):
    """
    Concrete implementation of the Memory abstract base class.

    This class provides methods to manage memory units, including creation, retrieval,
    updating, deletion, filtering, grouping, structurizing, skillizing, parameterizing,
    and more. It delegates specific operations to specialized components like
    MemoryCleaner, MemoryOrganizer, MemoryRetriever, MemoryStructurer, MemorySkillizer,
    and MemoryParameterizer.
    """

    def __init__(self, config: Dict):
        """
        Initialize the MemoryPalace with the provided configuration.

        Args:
            config (MemoryConfig): Configuration settings for the MemoryPalace.
        """
        self.config_dict = config
        self.config = None
        self.storage = None
        self.embedder = None
        self.cleaner = None
        self.organizer = None
        self.retriever = None
        self.structurer = None
        self.skillizer = None
        self.parameterizer = None
        self.setup()

    def setup(self):
        """
        Setup the MemoryPalace by initializing all components.
        """
        try:
            # Initialize EmbedderConfig
            embedder_config_dict = self.config_dict.get('embedder_config', {})
            self.embedder = Embedder(embedder_config_dict)

            storage_config_dict = self.config_dict.get('storage_config', {})
            self.storage = MemoryStorage(storage_config_dict) 

            # Initialize Memory Configuration
            self.config = MemoryConfig(
                embedder_config=self.embedder.config,
                storage_config=self.storage.config
            )

            logger.info("MemoryPalace: MemoryStorage and Embedder initialized successfully.")

            # Initialize specialized components
            self.cleaner = MemoryCleaner()
            self.organizer = MemoryOrganizer()
            self.retriever = MemoryRetriever(embedder=self.embedder, storage=self.storage)
            self.structurer = MemoryStructurer()
            self.skillizer = MemorySkillizer()
            self.parameterizer = MemoryParameterizer()
            logger.info("MemoryPalace: Specialized components initialized successfully.")

        except Exception as e:
            logger.error(f"MemoryPalace setup failed: {e}")
            self.handle_error(e)
            raise

    # CRUD Operations

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
            if embedding_response.get("data"):
                memory_unit.embedding = embedding_response["data"][0].get("embedding")
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
            # Delegate update operations to MemoryStorage
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
            self.storage.delete_all_memory_units()  # TODO: seems no work correctly, need to check
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
                logger.info("Save operation delegated to MemoryStorage.")
                # Example: self.storage.persist_changes()
        except Exception as e:
            logger.error(f"Error saving MemoryUnits: {e}")
            self.handle_error(e)
            raise

    # Delegated Operations

    def filter(self, criteria: Dict[str, Any]) -> List[MemoryUnit]:
        """
        Filters memory units based on the given criteria.

        Args:
            criteria (Dict[str, Any]): A dictionary of filter conditions.

        Returns:
            List[MemoryUnit]: A list of memory units matching the criteria.
        """
        try:
            memory_units = self.get_all()
            filter_type = criteria.get('filter_type')
            if not filter_type:
                raise ValueError("Missing 'filter_type' in criteria.")

            # Delegate filtering to MemoryCleaner
            filtered_memories = self.cleaner.filter(memory_units, filter_type, **criteria)
            logger.info(f"Filtered memories based on criteria: {criteria}")
            return filtered_memories
        except Exception as e:
            logger.error(f"Error filtering memories: {e}")
            self.handle_error(e)
            raise

    def organize(self, unit_ids: List[str], organize_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Groups memory units into a meaningful group.

        Args:
            unit_ids (List[str]): A list of memory unit IDs to group.
            organize_type (str): The type of group (e.g., 'dialogue_session', 'procedure').
            metadata (Optional[Dict[str, Any]]): Additional metadata for the group.

        Returns:
            str: A unique identifier for the created group.
        """
        try:
            # Retrieve the memory units to group
            memory_units = [self.get(unit_id) for unit_id in unit_ids]
            logger.debug(f"Grouping {len(memory_units)} MemoryUnits into group_type='{organize_type}'.")

            # Delegate grouping to MemoryOrganizer
            organized_memories = self.organizer.organize(memory_units, organize_type, metadata=metadata)
            logger.info(f"Grouped memories into '{organize_type}'. Total memory units after grouping: {len(organized_memories)}")
            return "group_id_placeholder"  # Replace with actual group ID if applicable
        except Exception as e:
            logger.error(f"Error grouping memories: {e}")
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
        try:
            # Retrieve the memory units to structurize
            memory_units = [self.get(uid) for uid in unit_ids]
            logger.debug(f"Structurizing {len(memory_units)} MemoryUnits with structure_type='{structure_type}'.")

            # Delegate structuring to MemoryStructurer
            self.structurer.structure(memory_units, structure_type, **kwargs)
            logger.info(f"Structurized memories with structure_type='{structure_type}'.")
        except Exception as e:
            logger.error(f"Error structurizing memories: {e}")
            self.handle_error(e)
            raise

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
        try:
            # Retrieve the memory units to skillize
            memory_units = [self.get(uid) for uid in unit_ids]
            logger.debug(f"Skillizing {len(memory_units)} MemoryUnits into skill_name='{skill_name}'.")

            # Delegate skillizing to MemorySkillizer
            skill_id = self.skillizer.skillize(memory_units, skill_name, **kwargs)
            logger.info(f"Skillized memories into skill with ID: {skill_id}")
            return skill_id
        except Exception as e:
            logger.error(f"Error skillizing memories: {e}")
            self.handle_error(e)
            raise

    def parameterize(self, **kwargs) -> None:
        """
        Trains a parametric model using the memory data.

        Args:
            **kwargs: Additional parameters for the training process.
        """
        try:
            # Retrieve all memory units
            memory_units = self.get_all()
            logger.debug(f"Parameterizing {len(memory_units)} MemoryUnits.")

            # Delegate parameterizing to MemoryParameterizer
            self.parameterizer.parameterize(memory_units, **kwargs)
            logger.info("Parameterized memories successfully.")
        except Exception as e:
            logger.error(f"Error parameterizing memories: {e}")
            self.handle_error(e)
            raise

    def retrieve(self, query: Any, retrieve_type: str, **kwargs) -> List[MemoryUnit]:
        """
        Retrieve data from memory based on a query.

        Args:
            query (Any): The query or criteria to retrieve specific memory data.
            retrieve_type (str): The type of retrieval (e.g., 'similar', 'related').
            **kwargs: Additional parameters for the retrieval process.

        Returns:
            List[MemoryUnit]: The retrieved memory data.
        """
        try:
            # Delegate retrieval to MemoryRetriever
            memories = self.retriever.retrieve(query=query, retrieve_type=retrieve_type, **kwargs)
            logger.info(f"Retrieved {len(memories)} memories using retrieve_type='{retrieve_type}'.")
            return memories
        except Exception as e:
            logger.error(f"Error retrieving MemoryUnits: {e}")
            self.handle_error(e)
            raise

    def embed(self, unit_id: str) -> None:
        """
        Generates an embedding for a memory unit.

        Args:
            unit_id (str): The unique identifier of the memory unit.
        """
        try:
            # Delegate embedding to MemoryRetriever
            memory_units = self.retriever.retrieve(query=unit_id, retrieve_type='similar', top_k=1)
            if not memory_units:
                raise ValueError(f"No MemoryUnit found with ID {unit_id} to embed.")

            memory_unit = memory_units[0]

            # Generate embedding using the embedder
            embedding_response = self.embedder.embed(memory_unit.content)
            if embedding_response.get("data") and len(embedding_response["data"]) > 0:
                memory_unit.embedding = embedding_response["data"][0].get("embedding")
            else:
                raise ValueError("Failed to generate embedding for the content.")

            # Update the memory unit with the new embedding
            self.update(unit_id, {'embedding': memory_unit.embedding})

            logger.info(f"Generated embedding for MemoryUnit ID: {unit_id}")
        except Exception as e:
            logger.error(f"Error generating embedding for MemoryUnit ID {unit_id}: {e}")
            self.handle_error(e)
            raise

    # Error Handling

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur during memory operations.

        Args:
            error (Exception): The exception that was raised.
        """
        logger.error(f"MemoryPalace encountered an error: {error}")
        # Additional error handling can be implemented here

    @staticmethod
    def get_api_key(self, config_section: Dict[str, Any], key_field: str, env_var_field: str) -> Optional[str]:
        """
        Retrieve an API key from the configuration section.

        Args:
            config_section (Dict[str, Any]): The configuration section (e.g., embedder_config).
            key_field (str): The key in the config_section that may contain the API key directly.
            env_var_field (str): The key in the config_section that specifies the environment variable name.

        Returns:
            Optional[str]: The API key if found, else None.

        Raises:
            EnvironmentError: If the environment variable is specified but not set.
        """
        # Check if API key is provided directly
        api_key = config_section.get(key_field)
        if api_key:
            logger.info(f"Using provided API key for '{key_field}'.")
            return api_key

        # Else, check if an environment variable is specified
        env_var = config_section.get(env_var_field)
        if env_var:
            api_key = os.getenv(env_var)
            if api_key:
                logger.info(f"Retrieved API key for '{key_field}' from environment variable '{env_var}'.")
                return api_key
            else:
                logger.error(f"Environment variable '{env_var}' for '{key_field}' is not set.")
                raise EnvironmentError(f"Environment variable '{env_var}' for '{key_field}' is not set.")
        
        logger.warning(f"No API key provided for '{key_field}'.")
        return None