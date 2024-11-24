# memory_storage.py

import logging
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import uuid4

from aeiva.cognition.memory.memory_unit import MemoryUnit
from aeiva.cognition.memory.memory_link import MemoryLink
from aeiva.storage.database_factory import DatabaseFactory
from aeiva.storage.database_factory import DatabaseConfigFactory

from aeiva.cognition.memory.storage_config import StorageConfig

logger = logging.getLogger(__name__)


class MemoryUnitRepository:
    """
    Repository for MemoryUnit to handle CRUD operations without SQLAlchemy.
    """

    def __init__(self, db: Any):
        """
        Initialize the repository with a DatabaseFactory instance.

        Args:
            db (Any): An instance of DatabaseFactory for relational databases.
        """
        self.db = db
        self.table_name = 'memory_units'
        self._create_table()

    def _create_table(self):
        """
        Creates the memory_units table if it does not exist.
        """
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            modality TEXT,
            type TEXT,
            status TEXT,
            tags TEXT,
            embedding TEXT,
            location TEXT,
            source_role TEXT,
            source_name TEXT,
            source_id TEXT,
            edges TEXT,
            metadata TEXT
        );
        """
        self.db.execute_sql(create_table_query)

    def add(self, memory_unit: MemoryUnit) -> None:
        """
        Adds a MemoryUnit to the relational database.

        Args:
            memory_unit (MemoryUnit): The memory unit to add.
        """
        insert_query = f"""
        INSERT INTO {self.table_name} (id, content, timestamp, modality, type, status, tags, embedding, location, 
            source_role, source_name, source_id, edges, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        data = (
            memory_unit.id,
            memory_unit.content,
            memory_unit.timestamp.isoformat(),
            memory_unit.modality,
            memory_unit.type,
            memory_unit.status,
            json.dumps(memory_unit.tags),
            json.dumps(memory_unit.embedding) if memory_unit.embedding else None,
            json.dumps(memory_unit.location) if memory_unit.location else None,
            memory_unit.source_role,
            memory_unit.source_name,
            memory_unit.source_id,
            json.dumps([link.to_dict() for link in memory_unit.edges]),
            json.dumps(memory_unit.metadata) if memory_unit.metadata else None
        )
        self.db.execute_sql(insert_query, data)

    def get(self, unit_id: str) -> Optional[MemoryUnit]:
        """
        Retrieves a MemoryUnit by its ID.

        Args:
            unit_id (str): The unique identifier of the memory unit.

        Returns:
            Optional[MemoryUnit]: The retrieved memory unit or None if not found.
        """
        select_query = f"SELECT * FROM {self.table_name} WHERE id = ?;"
        result = self.db.execute_sql(select_query, (unit_id,))
        row = result.fetchone()
        if row:
            return self._row_to_memory_unit(row)
        return None

    def update(self, memory_unit: MemoryUnit) -> None:
        """
        Updates an existing MemoryUnit in the relational database.

        Args:
            memory_unit (MemoryUnit): The memory unit with updated data.
        """
        update_query = f"""
        UPDATE {self.table_name}
        SET content = ?, timestamp = ?, modality = ?, type = ?, status = ?, tags = ?, embedding = ?, 
            location = ?, source_role = ?, source_name = ?, source_id = ?, edges = ?, metadata = ?
        WHERE id = ?;
        """
        data = (
            memory_unit.content,
            memory_unit.timestamp.isoformat(),
            memory_unit.modality,
            memory_unit.type,
            memory_unit.status,
            json.dumps(memory_unit.tags),
            json.dumps(memory_unit.embedding) if memory_unit.embedding else None,
            json.dumps(memory_unit.location) if memory_unit.location else None,
            memory_unit.source_role,
            memory_unit.source_name,
            memory_unit.source_id,
            json.dumps([link.to_dict() for link in memory_unit.edges]),
            json.dumps(memory_unit.metadata) if memory_unit.metadata else None,
            memory_unit.id
        )
        self.db.execute_sql(update_query, data)

    def delete(self, unit_id: str) -> None:
        """
        Deletes a MemoryUnit from the relational database.

        Args:
            unit_id (str): The unique identifier of the memory unit to delete.
        """
        delete_query = f"DELETE FROM {self.table_name} WHERE id = ?;"
        self.db.execute_sql(delete_query, (unit_id,))

    def list_all(self) -> List[MemoryUnit]:
        """
        Retrieves all MemoryUnits from the relational database.

        Returns:
            List[MemoryUnit]: A list of all memory units.
        """
        select_query = f"SELECT * FROM {self.table_name};"
        results = self.db.execute_sql(select_query)
        return [self._row_to_memory_unit(row) for row in results.fetchall()]

    def delete_all(self) -> None:
        """
        Deletes all MemoryUnits from the relational database.
        """
        delete_query = f"DELETE FROM {self.table_name};"
        self.db.execute_sql(delete_query)

    def _row_to_memory_unit(self, row: Any) -> MemoryUnit:
        """
        Converts a database row to a MemoryUnit instance.

        Args:
            row (Any): A row fetched from the database.

        Returns:
            MemoryUnit: The corresponding MemoryUnit instance.
        """
        return MemoryUnit(
            id=row['id'],
            content=row['content'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            modality=row['modality'],
            type=row['type'],
            status=row['status'],
            tags=json.loads(row['tags']) if row['tags'] else [],
            embedding=json.loads(row['embedding']) if row['embedding'] else [],
            location=json.loads(row['location']) if row['location'] else {},
            source_role=row['source_role'],
            source_name=row['source_name'],
            source_id=row['source_id'],
            edges=[MemoryLink.from_dict(link) for link in json.loads(row['edges'])] if row['edges'] else [],
            metadata=json.loads(row['metadata']) if row['metadata'] else {}
        )


class MemoryEventRepository:
    """
    Repository for MemoryEvent to handle CRUD operations without SQLAlchemy.
    """

    def __init__(self, db: Any):
        """
        Initialize the repository with a DatabaseFactory instance.

        Args:
            db (Any): An instance of DatabaseFactory for relational databases.
        """
        self.db = db
        self.table_name = 'memory_events'
        self._create_table()

    def _create_table(self):
        """
        Creates the memory_events table if it does not exist.
        """
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            id TEXT PRIMARY KEY,
            memory_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            memory_data TEXT,
            previous_data TEXT
        );
        """
        self.db.execute_sql(create_table_query)

    def add(self, event: Dict[str, Any]) -> None:
        """
        Adds a MemoryEvent to the relational database.

        Args:
            event (Dict[str, Any]): The event data to add.
        """
        insert_query = f"""
        INSERT INTO {self.table_name} (id, memory_id, event_type, timestamp, memory_data, previous_data)
        VALUES (?, ?, ?, ?, ?, ?);
        """
        data = (
            event.get('id', uuid4().hex),
            event['memory_id'],
            event['event_type'],
            datetime.utcnow().isoformat(),  # TODO: revise utcnow.
            event.get('memory_data'),
            event.get('previous_data')
        )
        self.db.execute_sql(insert_query, data)

    def get(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a MemoryEvent by its ID.

        Args:
            event_id (str): The unique identifier of the event.

        Returns:
            Optional[Dict[str, Any]]: The event data or None if not found.
        """
        select_query = f"SELECT * FROM {self.table_name} WHERE id = ?;"
        result = self.db.execute_sql(select_query, (event_id,))
        row = result.fetchone()
        if row:
            return self._row_to_event(row)
        return None

    def delete_all(self) -> None:
        """
        Deletes all MemoryEvents from the relational database.
        """
        delete_query = f"DELETE FROM {self.table_name};"
        self.db.execute_sql(delete_query)

    def list_all(self) -> List[Dict[str, Any]]:
        """
        Retrieves all MemoryEvents from the relational database.

        Returns:
            List[Dict[str, Any]]: A list of all events.
        """
        select_query = f"SELECT * FROM {self.table_name};"
        results = self.db.execute_sql(select_query)
        return [self._row_to_event(row) for row in results.fetchall()]

    def _row_to_event(self, row: Any) -> Dict[str, Any]:
        """
        Converts a database row to an event dictionary.

        Args:
            row (Any): A row fetched from the database.

        Returns:
            Dict[str, Any]: The corresponding event data.
        """
        return {
            "id": row['id'],
            "memory_id": row['memory_id'],
            "event_type": row['event_type'],
            "timestamp": datetime.fromisoformat(row['timestamp']),
            "memory_data": json.loads(row['memory_data']) if row['memory_data'] else None,
            "previous_data": json.loads(row['previous_data']) if row['previous_data'] else None
        }


class MemoryStorage:
    """
    Handles storage operations for MemoryPalace, including interactions with vector,
    graph, and relational databases.
    """

    def __init__(self, config: Dict):
        """
        Initialize the MemoryStorage with the provided configuration.

        Args:
            config (Any): Configuration settings for MemoryStorage.
        """
        self.config_dict = config
        self.config = None
        self.setup()

    def setup(self) -> None:
        """
        Set up the MemoryStorage's components based on the provided configuration.
        """
        try:
            # Initialize Vector Database Configuration
            vector_db_conf_dict = self.config_dict.get('vector_db_config', {})
            vector_db_provider_name = vector_db_conf_dict.get('provider_name', 'milvus')
            vector_db_config = DatabaseConfigFactory.create(
                provider_name=vector_db_conf_dict.get('provider_name', 'milvus'),
                uri=vector_db_conf_dict.get('uri', 'storage/milvus_demo.db'),
                collection_name=vector_db_conf_dict.get('collection_name', 'test_collection'),
                embedding_model_dims=vector_db_conf_dict.get('embedding_model_dims', 1536),  # 'text-embedding-ada-002': 1536,
                metric_type=vector_db_conf_dict.get('metric_type', 'COSINE')
            )

            # Initialize Graph Database Configuration
            graph_db_conf_dict = self.config_dict.get('graph_db_config', {})
            graph_db_provider_name = graph_db_conf_dict.get('provider_name', 'neo4j')
            graph_db_password = graph_db_conf_dict.get('password')
            graph_db_config = DatabaseConfigFactory.create(
                provider_name=graph_db_conf_dict.get('provider_name', 'neo4j'),
                uri=graph_db_conf_dict.get('uri', 'bolt://localhost:7687'),
                user=graph_db_conf_dict.get('user', 'neo4j'),
                password=graph_db_password,
                database=graph_db_conf_dict.get('database', 'neo4j'),
                encrypted=graph_db_conf_dict.get('encrypted', False)
            )

            # Initialize Relational Database Configuration
            relational_db_conf_dict = self.config_dict.get('relational_db_config', {})
            relational_db_provider_name = relational_db_conf_dict.get('provider_name', 'sqlite')
            relational_db_config = DatabaseConfigFactory.create(
                provider_name=relational_db_conf_dict.get('provider_name', 'sqlite'),
                database=relational_db_conf_dict.get('database', 'storage/test_database.db')
            )

            self.config = StorageConfig(
                vector_db_provider=self.config_dict.get('vector_db_provider', 'milvus'),
                vector_db_config=vector_db_config,
                graph_db_provider=self.config_dict.get('graph_db_provider', 'neo4j'),
                graph_db_config=graph_db_config,
                relational_db_provider=self.config_dict.get('relational_db_provider', 'sqlite'),
                relational_db_config=relational_db_config,
            )

            # Initialize the vector database
            self.vector_db = DatabaseFactory.create(
                provider_name=vector_db_provider_name,
                config=self.config.vector_db_config
            )

            # Initialize the graph database if provided
            if graph_db_provider_name and self.config.graph_db_config:
                self.graph_db = DatabaseFactory.create(
                    provider_name=graph_db_provider_name,
                    config=self.config.graph_db_config
                )
            else:
                self.graph_db = None

            # Initialize the relational database if provided
            if relational_db_provider_name and self.config.relational_db_config:
                self.relational_db = DatabaseFactory.create(
                    provider_name=relational_db_provider_name,
                    config=self.config.relational_db_config
                )
                self.memory_unit_repo = MemoryUnitRepository(self.relational_db)
                self.memory_event_repo = MemoryEventRepository(self.relational_db)
            else:
                self.relational_db = None
                self.memory_unit_repo = None
                self.memory_event_repo = None

            logger.info("MemoryStorage setup completed successfully.")
        except Exception as e:
            logger.error(f"Error during MemoryStorage setup: {e}")
            self.handle_error(e)
            raise  # Re-raise the exception after logging

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur during storage operations.

        Args:
            error (Exception): The exception that was raised.
        """
        logger.error(f"MemoryStorage encountered an error: {error}")
        # Additional error handling can be implemented here

    def add_memory_unit(self, memory_unit: MemoryUnit) -> None:
        """
        Adds a MemoryUnit to all configured databases.

        Args:
            memory_unit (MemoryUnit): The memory unit to add.
        """
        try:
            # Add to vector database
            self._add_to_vector_db(memory_unit)

            # Add to graph database
            if self.graph_db:
                self._add_to_graph_db(memory_unit)

            # Add to relational database
            if self.relational_db and self.memory_unit_repo:
                self._add_to_relational_db(memory_unit)

            # Record creation event
            if self.relational_db and self.memory_event_repo:
                self._record_event(
                    event_type="CREATE",
                    memory_unit=memory_unit
                )

            logger.info(f"Added MemoryUnit with ID: {memory_unit.id} to all databases.")
        except Exception as e:
            logger.error(f"Error adding MemoryUnit to databases: {e}")
            self.handle_error(e)
            raise

    def get_memory_unit(self, unit_id: str) -> MemoryUnit:
        """
        Retrieves a MemoryUnit by its unique identifier from the relational database.

        Args:
            unit_id (str): The unique identifier of the memory unit.

        Returns:
            MemoryUnit: The retrieved memory unit.
        """
        try:
            if not self.relational_db or not self.memory_unit_repo:
                raise ValueError("Relational database is not configured.")

            memory_unit = self.memory_unit_repo.get(unit_id)
            if not memory_unit:
                raise ValueError(f"MemoryUnit with ID {unit_id} does not exist.")

            logger.info(f"Retrieved MemoryUnit with ID: {unit_id} from Relational DB.")
            return memory_unit
        except Exception as e:
            logger.error(f"Error retrieving MemoryUnit with ID {unit_id}: {e}")
            self.handle_error(e)
            raise

    def update_memory_unit(self, unit_id: str, updates: Dict[str, Any]) -> None:
        """
        Updates a MemoryUnit in all configured databases.

        Args:
            unit_id (str): The unique identifier of the memory unit.
            updates (Dict[str, Any]): The updates to apply.
        """
        try:
            # Retrieve existing MemoryUnit
            memory_unit = self.get_memory_unit(unit_id)
            previous_state = memory_unit.to_dict()

            # Apply updates
            for key, value in updates.items():
                setattr(memory_unit, key, value)

            # Update in vector database
            self._update_vector_db(memory_unit)

            # Update in graph database
            if self.graph_db:
                self._update_graph_db(memory_unit)

            # Update in relational database
            if self.relational_db and self.memory_unit_repo:
                self._update_relational_db(memory_unit)

            # Record update event
            if self.relational_db and self.memory_event_repo:
                self._record_event(
                    event_type="UPDATE",
                    memory_unit=memory_unit,
                    previous_state=previous_state
                )

            logger.info(f"Updated MemoryUnit with ID: {unit_id} in all databases.")
        except Exception as e:
            logger.error(f"Error updating MemoryUnit with ID {unit_id}: {e}")
            self.handle_error(e)
            raise

    def delete_memory_unit(self, unit_id: str) -> None:
        """
        Deletes a MemoryUnit from all configured databases.

        Args:
            unit_id (str): The unique identifier of the memory unit.
        """
        try:
            # Retrieve existing MemoryUnit
            memory_unit = self.get_memory_unit(unit_id)

            # Delete from vector database
            self._delete_from_vector_db(unit_id)

            # Delete from graph database
            if self.graph_db:
                self._delete_from_graph_db(unit_id)

            # Delete from relational database
            if self.relational_db and self.memory_unit_repo:
                self._delete_relational_db(unit_id)

            # Record deletion event
            if self.relational_db and self.memory_event_repo:
                self._record_event(
                    event_type="DELETE",
                    memory_unit=memory_unit
                )

            logger.info(f"Deleted MemoryUnit with ID: {unit_id} from all databases.")
        except Exception as e:
            logger.error(f"Error deleting MemoryUnit with ID {unit_id}: {e}")
            self.handle_error(e)
            raise

    def get_all_memory_units(self) -> List[MemoryUnit]:
        """
        Retrieves all MemoryUnits from the relational database.

        Returns:
            List[MemoryUnit]: A list of all memory units.
        """
        try:
            if not self.relational_db or not self.memory_unit_repo:
                raise ValueError("Relational database is not configured.")

            memory_units = self.memory_unit_repo.list_all()
            logger.info(f"Retrieved all MemoryUnits from Relational DB. Total count: {len(memory_units)}")
            return memory_units
        except Exception as e:
            logger.error(f"Error retrieving all MemoryUnits: {e}")
            self.handle_error(e)
            raise

    def delete_all_memory_units(self) -> None:
        """
        Deletes all MemoryUnits from all configured databases.
        """
        try:
            # Delete from vector database
            self.vector_db.delete_collection(
                collection_name=self.config.vector_db_config.collection_name
            )

            # Delete all nodes from graph database
            if self.graph_db:
                self.graph_db.delete_all()

            # Delete all records from relational database
            if self.relational_db and self.memory_unit_repo and self.memory_event_repo:
                self.memory_unit_repo.delete_all()
                self.memory_event_repo.delete_all()

            logger.info("Deleted all MemoryUnits from all databases.")
        except Exception as e:
            logger.error(f"Error deleting all MemoryUnits: {e}")
            self.handle_error(e)
            raise

    # Internal helper methods

    def _add_to_vector_db(self, memory_unit: MemoryUnit) -> None:
        """
        Adds the embedding vector of a MemoryUnit to the vector database.

        Args:
            memory_unit (MemoryUnit): The memory unit to add.
        """
        try:
            # Ensure embedding exists
            if not memory_unit.embedding:
                raise ValueError("MemoryUnit does not have an embedding.")

            # Prepare payload with essential fields
            payload = {
                "id": memory_unit.id,
                "type": memory_unit.type,
                "modality": memory_unit.modality
            }

            # Insert into vector database
            self.vector_db.insert_vectors(
                collection_name=self.config.vector_db_config.collection_name,
                vectors=[memory_unit.embedding],
                payloads=[payload],
                ids=[memory_unit.id]
            )

            logger.info(f"Inserted embedding for MemoryUnit ID: {memory_unit.id} into Vector DB.")
        except Exception as e:
            logger.error(f"Error adding MemoryUnit to Vector DB: {e}")
            self.handle_error(e)
            raise

    def _update_vector_db(self, memory_unit: MemoryUnit) -> None:
        """
        Updates the embedding vector of a MemoryUnit in the vector database.

        Args:
            memory_unit (MemoryUnit): The memory unit to update.
        """
        try:
            if not memory_unit.embedding:
                raise ValueError("MemoryUnit does not have an embedding.")

            payload = {
                "type": memory_unit.type,
                "modality": memory_unit.modality
            }

            self.vector_db.update_vector(
                collection_name=self.config.vector_db_config.collection_name,
                vector_id=memory_unit.id,
                vector=memory_unit.embedding,
                payload=payload
            )

            logger.info(f"Updated embedding for MemoryUnit ID: {memory_unit.id} in Vector DB.")
        except Exception as e:
            logger.error(f"Error updating MemoryUnit in Vector DB: {e}")
            self.handle_error(e)
            raise

    def _delete_from_vector_db(self, unit_id: str) -> None:
        """
        Deletes a MemoryUnit's embedding from the vector database.

        Args:
            unit_id (str): The unique identifier of the memory unit.
        """
        try:
            self.vector_db.delete_vector(
                collection_name=self.config.vector_db_config.collection_name,
                vector_id=unit_id
            )

            logger.info(f"Deleted embedding for MemoryUnit ID: {unit_id} from Vector DB.")
        except Exception as e:
            logger.error(f"Error deleting MemoryUnit from Vector DB: {e}")
            self.handle_error(e)
            raise

    def _add_to_graph_db(self, memory_unit: MemoryUnit) -> None:
        """
        Adds a MemoryUnit as a node in the graph database and establishes relationships.

        Args:
            memory_unit (MemoryUnit): The memory unit to add.
        """
        try:
            # Serialize complex fields
            properties = {
                "id": memory_unit.id,
                "content": memory_unit.content,
                "timestamp": memory_unit.timestamp.isoformat(),
                "modality": memory_unit.modality,
                "type": memory_unit.type,
                "status": memory_unit.status,
                "tags": memory_unit.tags,
                "embedding": memory_unit.embedding,
                "location": json.dumps(memory_unit.location) if memory_unit.location else None,  # Serialized
                "source_role": memory_unit.source_role,
                "source_name": memory_unit.source_name,
                "source_id": memory_unit.source_id,
                "metadata": json.dumps(memory_unit.metadata) if memory_unit.metadata else None  # Serialized
            }

            # Add node to graph database
            self.graph_db.add_node(
                node_id=memory_unit.id,
                properties=properties,
                labels=[memory_unit.type or 'MemoryUnit']
            )

            logger.info(f"Added MemoryUnit ID: {memory_unit.id} to Graph DB.")

            # Add relationships (edges) if any
            for link in memory_unit.edges:
                # Serialize edge metadata if necessary
                edge_properties = {}
                if link.metadata:
                    edge_properties['metadata'] = json.dumps(link.metadata)

                self.graph_db.add_edge(
                    source_id=link.source_id,
                    target_id=link.target_id,
                    relationship=link.relationship,
                    properties=edge_properties
                )

            logger.info(f"Added {len(memory_unit.edges)} edges for MemoryUnit ID: {memory_unit.id} in Graph DB.")
        except Exception as e:
            logger.error(f"Error adding MemoryUnit to Graph DB: {e}")
            self.handle_error(e)
            raise

    def _update_graph_db(self, memory_unit: MemoryUnit) -> None:
        """
        Updates a MemoryUnit in the graph database.

        Args:
            memory_unit (MemoryUnit): The memory unit to update.
        """
        try:
            # Update node properties
            properties = {
                "content": memory_unit.content,
                "timestamp": memory_unit.timestamp.isoformat(),
                "modality": memory_unit.modality,
                "type": memory_unit.type,
                "status": memory_unit.status,
                "tags": memory_unit.tags,
                "embedding": memory_unit.embedding,
                "location": json.dumps(memory_unit.location) if memory_unit.location else None,  # Serialized
                "source_role": memory_unit.source_role,
                "source_name": memory_unit.source_name,
                "source_id": memory_unit.source_id,
                "metadata": json.dumps(memory_unit.metadata) if memory_unit.metadata else None  # Serialized
            }

            self.graph_db.update_node(
                node_id=memory_unit.id,
                properties=properties
            )

            # Handle edges updates as needed
            # This can be complex and depends on your specific requirements

            logger.info(f"Updated MemoryUnit ID: {memory_unit.id} in Graph DB.")
        except Exception as e:
            logger.error(f"Error updating MemoryUnit in Graph DB: {e}")
            self.handle_error(e)
            raise

    def _delete_from_graph_db(self, unit_id: str) -> None:
        """
        Deletes a MemoryUnit from the graph database.

        Args:
            unit_id (str): The unique identifier of the memory unit.
        """
        try:
            self.graph_db.delete_node(node_id=unit_id)
            logger.info(f"Deleted MemoryUnit ID: {unit_id} from Graph DB.")
        except Exception as e:
            logger.error(f"Error deleting MemoryUnit from Graph DB: {e}")
            self.handle_error(e)
            raise

    def _add_to_relational_db(self, memory_unit: MemoryUnit) -> None:
        """
        Adds a MemoryUnit to the relational database.

        Args:
            memory_unit (MemoryUnit): The memory unit to add.
        """
        try:
            self.memory_unit_repo.add(memory_unit)
            logger.info(f"Inserted MemoryUnit ID: {memory_unit.id} into Relational DB.")
        except Exception as e:
            logger.error(f"Error adding MemoryUnit to Relational DB: {e}")
            raise

    def _update_relational_db(self, memory_unit: MemoryUnit) -> None:
        """
        Updates a MemoryUnit in the relational database.

        Args:
            memory_unit (MemoryUnit): The memory unit to update.
        """
        try:
            self.memory_unit_repo.update(memory_unit)
            logger.info(f"Updated MemoryUnit ID: {memory_unit.id} in Relational DB.")
        except Exception as e:
            logger.error(f"Error updating MemoryUnit in Relational DB: {e}")
            raise

    def _delete_relational_db(self, unit_id: str) -> None:
        """
        Deletes a MemoryUnit from the relational database.

        Args:
            unit_id (str): The unique identifier of the memory unit.
        """
        try:
            self.memory_unit_repo.delete(unit_id)
            logger.info(f"Deleted MemoryUnit ID: {unit_id} from Relational DB.")
        except Exception as e:
            logger.error(f"Error deleting MemoryUnit from Relational DB: {e}")
            raise

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
                "memory_id": memory_unit.id,
                "event_type": event_type,
                "memory_data": json.dumps(memory_unit.to_dict()),
                "previous_data": json.dumps(previous_state) if previous_state else None
            }

            self.memory_event_repo.add(event_record)
            logger.info(f"Recorded event '{event_type}' for MemoryUnit ID: {memory_unit.id}.")
        except Exception as e:
            logger.error(f"Error recording event in Relational DB: {e}")
            raise

    def retrieve_similar_memory_units(self, query_embedding: List[float], top_k: int) -> List[MemoryUnit]:
        """
        Retrieves memory units similar to the given embedding.

        Args:
            query_embedding (List[float]): The embedding vector of the query.
            top_k (int): The number of similar units to retrieve.

        Returns:
            List[MemoryUnit]: A list of similar memory units.
        """
        try:
            # Perform similarity search
            results = self.vector_db.search_vectors(
                collection_name=self.config.vector_db_config.collection_name,
                query_vector=query_embedding,
                top_k=top_k
            )

            memory_units = []
            for result in results:
                unit_id = result['id']
                memory_unit = self.get_memory_unit(unit_id)
                memory_units.append(memory_unit)

            logger.info(f"Retrieved {len(memory_units)} similar MemoryUnits.")
            return memory_units
        except Exception as e:
            logger.error(f"Error retrieving similar MemoryUnits: {e}")
            self.handle_error(e)
            raise

    def retrieve_related_memory_units(self, unit_id: str, relationship: Optional[str] = None) -> List[MemoryUnit]:
        """
        Retrieves memory units related to the given one based on relationships.

        Args:
            unit_id (str): The unique identifier of the memory unit.
            relationship (Optional[str]): Filter by relationship type.

        Returns:
            List[MemoryUnit]: A list of related memory units.
        """
        try:
            if not self.graph_db:
                raise ValueError("Graph database is not configured.")

            # Retrieve related nodes from graph database
            neighbors = self.graph_db.get_neighbors(
                node_id=unit_id,
                relationship=relationship
            )

            related_units = []
            for neighbor in neighbors:
                related_unit = self.get_memory_unit(neighbor['id'])
                related_units.append(related_unit)

            logger.info(f"Retrieved {len(related_units)} related MemoryUnits.")
            return related_units
        except Exception as e:
            logger.error(f"Error retrieving related MemoryUnits: {e}")
            self.handle_error(e)
            raise
