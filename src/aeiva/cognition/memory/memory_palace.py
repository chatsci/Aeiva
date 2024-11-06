# memory_palace.py

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import uuid4
from dataclasses import asdict  # Import asdict to convert dataclasses to dicts

from aeiva.cognition.memory.memory_unit import MemoryUnit
from aeiva.cognition.memory.memory_link import MemoryLink
from aeiva.cognition.memory.memory import Memory
from aeiva.cognition.memory.memory_config import MemoryConfig
from aeiva.embedding.embedder_config import EmbedderConfig
from aeiva.embedding.embedder import Embedder
from aeiva.storage.database_factory import DatabaseConfigFactory, DatabaseFactory

logger = logging.getLogger(__name__)


class MemoryPalace(Memory):
    """
    Concrete implementation of the Memory abstract base class.

    This class provides methods to manage memory units, including creation, retrieval,
    updating, deletion, filtering, grouping, and more.
    """

    def __init__(self, config: MemoryConfig):
        """
        Initialize the MemoryPalace with the provided configuration.

        Args:
            config (MemoryConfig): Configuration settings for the MemoryPalace.
        """
        self.config = config
        self.setup()

    def setup(self) -> None:
        """
        Set up the MemoryPalace's components based on the provided configuration.
        """
        try:
            # Initialize the embedding model
            embedder_config = EmbedderConfig(
                provider_name=self.config.embedder_config.provider_name,
                model_name=self.config.embedder_config.model_name,
                api_key=self.config.embedder_config.api_key  # Replace with your actual API key
            )
            self.embedder = Embedder(embedder_config)

            # Initialize the language model (LLM)
            self.llm = LLMFactory.create(
                provider_name=self.config.llm_config.provider_name,
                config=self.config.llm_config
            )

            # Convert vector_db_config to dict
            vector_db_config_dict = asdict(self.config.vector_db_config)
            # Initialize the vector database
            self.vector_db = DatabaseFactory.create(
                provider_name=self.config.vector_db_config.provider_name,
                **vector_db_config_dict
            )

            # Initialize the graph database if provided
            if self.config.graph_db_config:
                # Convert graph_db_config to dict
                graph_db_config_dict = asdict(self.config.graph_db_config)
                self.graph_db = DatabaseFactory.create(
                    provider_name=self.config.graph_db_config.provider_name,
                    **graph_db_config_dict
                )
            else:
                self.graph_db = None

            # Initialize the relational database if provided
            if self.config.relational_db_config:
                # Convert relational_db_config to dict
                relational_db_config_dict = asdict(self.config.relational_db_config)
                self.relational_db = DatabaseFactory.create(
                    provider_name=self.config.relational_db_config.provider_name,
                    **relational_db_config_dict
                )
            else:
                self.relational_db = None

            logger.info("MemoryPalace setup completed successfully.")
        except Exception as e:
            logger.error(f"Error during MemoryPalace setup: {e}")
            self.handle_error(e)

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
            # Create a new MemoryUnit
            memory_unit = MemoryUnit(
                content=content,
                **kwargs
            )

            # Generate embedding for the content
            memory_unit.embedding = self.embedder.embed(content)

            # Insert into vector database
            self.vector_db.insert_vectors(
                collection_name=self.config.vector_db_config.collection_name,
                vectors=[memory_unit.embedding],
                payloads=[memory_unit.to_dict()],
                ids=[memory_unit.id]
            )

            # Optionally, add to graph database
            if self.graph_db:
                self._add_to_graph_db(memory_unit)

            # Optionally, record in relational database
            if self.relational_db:
                self._record_event(
                    event_type="CREATE",
                    memory_unit=memory_unit
                )

            logger.info(f"Created new memory unit with ID: {memory_unit.id}")
            return memory_unit
        except Exception as e:
            logger.error(f"Error creating memory unit: {e}")
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
            # Retrieve from vector database
            vector_data = self.vector_db.get_vector(
                collection_name=self.config.vector_db_config.collection_name,
                vector_id=unit_id
            )
            memory_unit = MemoryUnit.from_dict(vector_data['payload'])
            logger.info(f"Retrieved memory unit with ID: {unit_id}")
            return memory_unit
        except Exception as e:
            logger.error(f"Error retrieving memory unit with ID {unit_id}: {e}")
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
            # Retrieve existing memory unit
            memory_unit = self.get(unit_id)
            previous_state = memory_unit.to_dict()

            # Update fields
            for key, value in updates.items():
                setattr(memory_unit, key, value)

            # Update embedding if content has changed
            if 'content' in updates:
                memory_unit.embedding = self.embedder.embed(memory_unit.content)

            # Update in vector database
            self.vector_db.update_vector(
                collection_name=self.config.vector_db_config.collection_name,
                vector_id=unit_id,
                vector=memory_unit.embedding,
                payload=memory_unit.to_dict()
            )

            # Optionally, update in graph database
            if self.graph_db:
                self._update_graph_db(memory_unit)

            # Optionally, record in relational database
            if self.relational_db:
                self._record_event(
                    event_type="UPDATE",
                    memory_unit=memory_unit,
                    previous_state=previous_state
                )

            logger.info(f"Updated memory unit with ID: {unit_id}")
        except Exception as e:
            logger.error(f"Error updating memory unit with ID {unit_id}: {e}")
            self.handle_error(e)
            raise

    def delete(self, unit_id: str) -> None:
        """
        Deletes a memory unit by its unique identifier.

        Args:
            unit_id (str): The unique identifier of the memory unit.
        """
        try:
            # Retrieve existing memory unit for logging or relational db
            memory_unit = self.get(unit_id)

            # Delete from vector database
            self.vector_db.delete_vector(
                collection_name=self.config.vector_db_config.collection_name,
                vector_id=unit_id
            )

            # Optionally, delete from graph database
            if self.graph_db:
                self._delete_from_graph_db(unit_id)

            # Optionally, record in relational database
            if self.relational_db:
                self._record_event(
                    event_type="DELETE",
                    memory_unit=memory_unit
                )

            logger.info(f"Deleted memory unit with ID: {unit_id}")
        except Exception as e:
            logger.error(f"Error deleting memory unit with ID {unit_id}: {e}")
            self.handle_error(e)
            raise

    def get_all(self) -> List[MemoryUnit]:
        """
        Retrieves all memory units.

        Returns:
            List[MemoryUnit]: A list of all memory units.
        """
        try:
            # Retrieve all vectors from vector database
            vectors = self.vector_db.list_vectors(
                collection_name=self.config.vector_db_config.collection_name
            )

            memory_units = [MemoryUnit.from_dict(vector['payload']) for vector in vectors]
            logger.info(f"Retrieved all memory units. Total count: {len(memory_units)}")
            return memory_units
        except Exception as e:
            logger.error(f"Error retrieving all memory units: {e}")
            self.handle_error(e)
            raise

    def delete_all(self) -> None:
        """
        Deletes all memory units.
        """
        try:
            # Delete the entire collection from vector database
            self.vector_db.delete_collection(
                collection_name=self.config.vector_db_config.collection_name
            )

            # Optionally, delete all nodes from graph database
            if self.graph_db:
                self.graph_db.delete_all_nodes()

            # Optionally, delete all records from relational database
            if self.relational_db:
                self.relational_db.delete_records(table="memory_events")

            logger.info("Deleted all memory units.")
        except Exception as e:
            logger.error(f"Error deleting all memory units: {e}")
            self.handle_error(e)
            raise

    def load(self) -> None:
        """
        Loads the memory from the database or file.
        """
        # Implementation depends on the storage mechanism.
        # For vector databases, data is usually loaded on demand.
        pass

    def save(self) -> None:
        """
        Saves the memory to the database or file.
        """
        # Implementation depends on the storage mechanism.
        # For vector databases, data is persisted automatically.
        pass

    def filter(self, criteria: Dict[str, Any]) -> List[MemoryUnit]:
        """
        Filters memory units based on the given criteria.

        Args:
            criteria (Dict[str, Any]): A dictionary of filter conditions.

        Returns:
            List[MemoryUnit]: A list of memory units matching the criteria.
        """
        try:
            # Use vector database's filtering capabilities
            vectors = self.vector_db.list_vectors(
                collection_name=self.config.vector_db_config.collection_name,
                filters=criteria
            )

            memory_units = [MemoryUnit.from_dict(vector['payload']) for vector in vectors]
            logger.info(f"Filtered memory units based on criteria: {criteria}")
            return memory_units
        except Exception as e:
            logger.error(f"Error filtering memory units: {e}")
            self.handle_error(e)
            raise

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
        try:
            group_id = uuid4().hex
            # Implement grouping logic, e.g., creating a new MemoryUnit representing the group
            group_unit = MemoryUnit(
                id=group_id,
                content=f"Group of type '{group_type}'",
                type=group_type,
                metadata=metadata or {}
            )

            # Optionally, add edges in graph database to represent relationships
            if self.graph_db:
                for unit_id in unit_ids:
                    link = MemoryLink(
                        id=unit_id,
                        relationship="grouped_in",
                        metadata={"group_type": group_type}
                    )
                    self.graph_db.add_edge(
                        source_id=unit_id,
                        target_id=group_id,
                        relationship=link.relationship,
                        properties=link.metadata
                    )

            logger.info(f"Created group with ID: {group_id}")
            return group_id
        except Exception as e:
            logger.error(f"Error grouping memory units: {e}")
            self.handle_error(e)
            raise

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

            # Use LLM to derive new content
            derived_content = self.llm.generate_response(
                prompt=f"Derive a {derivation_type} from the following content:\n{combined_content}",
                **kwargs
            )

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
        try:
            # Implement structuring logic, e.g., extracting entities and relationships
            # and adding them to the graph database
            if not self.graph_db:
                logger.warning("Graph database is not configured.")
                return

            for unit_id in unit_ids:
                memory_unit = self.get(unit_id)
                # Use LLM to extract entities and relationships
                extraction_result = self.llm.generate_response(
                    prompt=f"Extract entities and relationships from the following content:\n{memory_unit.content}",
                    **kwargs
                )
                # Parse and add to graph database
                # For simplicity, assume extraction_result is a list of (entity, relationship, entity) tuples
                # This is a placeholder for actual implementation
                for source, relationship, target in extraction_result:
                    self.graph_db.add_edge(
                        source_id=source,
                        target_id=target,
                        relationship=relationship
                    )

            logger.info(f"Structured memory units into {structure_type}.")
        except Exception as e:
            logger.error(f"Error structuring memory units: {e}")
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
            skill_id = uuid4().hex
            # Implement skill creation logic
            # For simplicity, we'll store skills as special MemoryUnits
            skill_content = f"Skill '{skill_name}' created from units: {unit_ids}"
            skill_unit = self.create(
                content=skill_content,
                type="skill",
                source_role="skill",
                metadata=kwargs.get('metadata')
            )

            logger.info(f"Created skill with ID: {skill_id}")
            return skill_id
        except Exception as e:
            logger.error(f"Error skillizing memory units: {e}")
            self.handle_error(e)
            raise

    def embed(self, unit_id: str) -> None:
        """
        Generates an embedding for a memory unit.

        Args:
            unit_id (str): The unique identifier of the memory unit.
        """
        try:
            memory_unit = self.get(unit_id)
            memory_unit.embedding = self.embedder.embed(memory_unit.content)
            self.update(unit_id, {'embedding': memory_unit.embedding})
            logger.info(f"Generated embedding for memory unit with ID: {unit_id}")
        except Exception as e:
            logger.error(f"Error generating embedding for memory unit: {e}")
            self.handle_error(e)
            raise

    def parameterize(self, **kwargs) -> None:
        """
        Trains a parametric model using the memory data.

        Args:
            **kwargs: Additional parameters for the training process.
        """
        # Placeholder for model training implementation
        logger.info("Parameterization is not implemented yet.")

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
            logger.error(f"Error retrieving memory units: {e}")
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
            query_embedding = self.embedder.embed(query)

            # Perform similarity search in vector database
            results = self.vector_db.search_vectors(
                collection_name=self.config.vector_db_config.collection_name,
                query_vector=query_embedding,
                top_k=top_k
            )

            memory_units = [MemoryUnit.from_dict(result['payload']) for result in results]
            logger.info(f"Retrieved {len(memory_units)} similar memory units.")
            return memory_units
        except Exception as e:
            logger.error(f"Error retrieving similar memory units: {e}")
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
            if not self.graph_db:
                logger.warning("Graph database is not configured.")
                return []

            # Assuming 'query' is a memory unit ID
            memory_unit = self.get(query)

            # Retrieve related nodes from graph database
            neighbors = self.graph_db.get_neighbors(
                node_id=memory_unit.id,
                relationship=relationship
            )

            related_units = []
            for neighbor in neighbors:
                related_unit = self.get(neighbor['id'])
                related_units.append(related_unit)

            logger.info(f"Retrieved {len(related_units)} related memory units.")
            return related_units
        except Exception as e:
            logger.error(f"Error retrieving related memory units: {e}")
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

    # Internal helper methods

    def _record_event(self, event_type: str, memory_unit: MemoryUnit, previous_state: Optional[Dict[str, Any]] = None) -> None:
        """
        Records an event in the relational database.

        Args:
            event_type (str): The type of event ('CREATE', 'UPDATE', 'DELETE').
            memory_unit (MemoryUnit): The memory unit involved in the event.
            previous_state (Optional[Dict[str, Any]]): The previous state of the memory unit (for updates).
        """
        try:
            event_record = {
                "id": uuid4().hex,
                "memory_id": memory_unit.id,
                "event_type": event_type,
                "timestamp": datetime.utcnow(),
                "memory_data": memory_unit.to_dict(),
                "previous_data": previous_state
            }
            self.relational_db.insert_record(
                table="memory_events",
                record=event_record
            )
            logger.info(f"Recorded event '{event_type}' for memory unit ID: {memory_unit.id}")
        except Exception as e:
            logger.error(f"Error recording event in relational database: {e}")
            self.handle_error(e)
            raise

    def _add_to_graph_db(self, memory_unit: MemoryUnit) -> None:
        """
        Adds a memory unit to the graph database.

        Args:
            memory_unit (MemoryUnit): The memory unit to add.
        """
        try:
            self.graph_db.add_node(
                node_id=memory_unit.id,
                properties=memory_unit.to_dict(),
                labels=[memory_unit.type or 'MemoryUnit']
            )

            # Add edges if any
            for link in memory_unit.edges:
                self.graph_db.add_edge(
                    source_id=memory_unit.id,
                    target_id=link.id,
                    relationship=link.relationship,
                    properties=link.metadata
                )
        except Exception as e:
            logger.error(f"Error adding memory unit to graph database: {e}")
            self.handle_error(e)
            raise

    def _update_graph_db(self, memory_unit: MemoryUnit) -> None:
        """
        Updates a memory unit in the graph database.

        Args:
            memory_unit (MemoryUnit): The memory unit to update.
        """
        try:
            self.graph_db.update_node(
                node_id=memory_unit.id,
                properties=memory_unit.to_dict()
            )
        except Exception as e:
            logger.error(f"Error updating memory unit in graph database: {e}")
            self.handle_error(e)
            raise

    def _delete_from_graph_db(self, unit_id: str) -> None:
        """
        Deletes a memory unit from the graph database.

        Args:
            unit_id (str): The unique identifier of the memory unit.
        """
        try:
            self.graph_db.delete_node(node_id=unit_id)
        except Exception as e:
            logger.error(f"Error deleting memory unit from graph database: {e}")
            self.handle_error(e)
            raise