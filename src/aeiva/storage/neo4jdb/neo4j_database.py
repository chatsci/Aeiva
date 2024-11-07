import logging
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase as Neo4jGraphDatabase  # to avoid name conflict with my own GraphDatabase
from neo4j import basic_auth, exceptions
from aeiva.storage.graph_database import GraphDatabase

logger = logging.getLogger(__name__)


class NodeNotFoundError(Exception):
    """Exception raised when a node is not found in the graph database."""
    pass


class StorageError(Exception):
    """Exception raised when there is a storage-related error in the graph database."""
    pass


class Neo4jDatabase(GraphDatabase):
    """
    Concrete implementation of GraphStoreBase using Neo4j.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the Neo4j graph database connection.

        Args:
            config (Dict[str, Any]): Configuration dictionary.
        """
        self.config = config
        self.uri = config.get('uri')
        self.user = config.get('user')
        self.password = config.get('password')
        self.database = config.get('database', 'neo4j')
        self.encrypted = config.get('encrypted', True)

        if not all([self.uri, self.user, self.password]):
            raise ValueError("Required configuration parameters 'uri', 'user', and 'password' are missing.")

        self.create_client(
            uri=self.uri,
            user=self.user,
            password=self.password,
            encrypted=self.encrypted
        )

    def create_client(
        self,
        uri: str,
        user: str,
        password: str,
        encrypted: bool = True,
        **kwargs
    ) -> None:
        """
        Initializes the client connection to the Neo4j graph database.

        Args:
            uri (str): The URI of the Neo4j instance.
            user (str): Username for authentication.
            password (str): Password for authentication.
            encrypted (bool): Whether to use encrypted connection.
            **kwargs: Additional parameters.

        Raises:
            ConnectionError: If the client fails to connect to the graph database.
        """
        try:
            auth = basic_auth(user, password)
            self.driver = Neo4jGraphDatabase.driver(uri, auth=auth, encrypted=encrypted, **kwargs)
            self.session = self.driver.session(database=self.database)
            logger.info(f"Connected to Neo4j at {uri}.")
        except exceptions.Neo4jError as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise ConnectionError(f"Failed to connect to Neo4j: {e}")

    def add_node(
        self,
        node_id: str,
        properties: Optional[Dict[str, Any]] = None,
        labels: Optional[List[str]] = None
    ) -> None:
        """
        Adds a node to the graph.

        Args:
            node_id (str): Unique identifier for the node.
            properties (Optional[Dict[str, Any]]): Properties associated with the node.
            labels (Optional[List[str]]): Labels or types associated with the node.

        Raises:
            StorageError: If there is an issue adding the node.
        """
        properties = properties or {}
        labels = labels or []
        labels_str = ':' + ':'.join(labels) if labels else ''
        cypher = f"MERGE (n{labels_str} {{id: $node_id}}) SET n += $properties"
        params = {
            'node_id': node_id,
            'properties': properties
        }
        try:
            self.session.run(cypher, params)
            logger.info(f"Node with id '{node_id}' added to the graph.")
        except exceptions.Neo4jError as e:
            logger.error(f"Failed to add node: {e}")
            raise StorageError(f"Failed to add node: {e}")

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Adds an edge (relationship) between two nodes.

        Args:
            source_id (str): Unique identifier of the source node.
            target_id (str): Unique identifier of the target node.
            relationship (str): Type of the relationship.
            properties (Optional[Dict[str, Any]]): Properties associated with the edge.

        Raises:
            NodeNotFoundError: If either the source or target node does not exist.
            StorageError: If there is an issue adding the edge.
        """
        properties = properties or {}
        # First, check if both nodes exist
        cypher_check = "MATCH (a {id: $source_id}), (b {id: $target_id}) RETURN a, b"
        params = {
            'source_id': source_id,
            'target_id': target_id
        }
        try:
            result = self.session.run(cypher_check, params)
            record = result.single()
            if not record:
                missing_nodes = []
                # Check if source node exists
                node_a_exists = self.session.run("MATCH (a {id: $source_id}) RETURN a", {'source_id': source_id}).single()
                if not node_a_exists:
                    missing_nodes.append(source_id)
                # Check if target node exists
                node_b_exists = self.session.run("MATCH (b {id: $target_id}) RETURN b", {'target_id': target_id}).single()
                if not node_b_exists:
                    missing_nodes.append(target_id)
                logger.warning(f"Node(s) with id(s) {missing_nodes} not found.")
                raise NodeNotFoundError(f"Node(s) with id(s) {missing_nodes} not found.")
            # Proceed to add the edge
            cypher_edge = (
                "MATCH (a {id: $source_id}), (b {id: $target_id}) "
                f"MERGE (a)-[r:{relationship}]->(b) "
                "SET r += $properties"
            )
            params['properties'] = properties
            self.session.run(cypher_edge, params)
            logger.info(f"Relationship '{relationship}' added between '{source_id}' and '{target_id}'.")
        except NodeNotFoundError:
            raise
        except exceptions.Neo4jError as e:
            logger.error(f"Failed to add edge: {e}")
            raise StorageError(f"Failed to add edge: {e}")

    def get_node(self, node_id: str) -> Dict[str, Any]:
        """
        Retrieves a node by its identifier.

        Args:
            node_id (str): Unique identifier of the node.

        Returns:
            Dict[str, Any]: A dictionary containing the node's properties and labels.

        Raises:
            NodeNotFoundError: If the node does not exist.
            StorageError: If there is an issue retrieving the node.
        """
        cypher = "MATCH (n {id: $node_id}) RETURN n"
        params = {'node_id': node_id}
        try:
            result = self.session.run(cypher, params)
            record = result.single()
            if record:
                node = record['n']
                node_data = {
                    'id': node['id'],
                    'properties': {k: v for k, v in node.items() if k != 'id'},
                    'labels': list(node.labels)
                }
                logger.info(f"Node with id '{node_id}' retrieved.")
                return node_data
            else:
                logger.warning(f"Node with id '{node_id}' not found.")
                raise NodeNotFoundError(f"Node with id '{node_id}' not found.")
        except exceptions.Neo4jError as e:
            logger.error(f"Failed to get node: {e}")
            raise StorageError(f"Failed to get node: {e}")

    def update_node(self, node_id: str, properties: Dict[str, Any]) -> None:
        """
        Updates properties of a node.

        Args:
            node_id (str): Unique identifier of the node.
            properties (Dict[str, Any]): Properties to update.

        Raises:
            NodeNotFoundError: If the node does not exist.
            StorageError: If there is an issue updating the node.
        """
        cypher = "MATCH (n {id: $node_id}) SET n += $properties RETURN n"
        params = {
            'node_id': node_id,
            'properties': properties
        }
        try:
            result = self.session.run(cypher, params)
            record = result.single()
            if record:
                logger.info(f"Node with id '{node_id}' updated.")
            else:
                logger.warning(f"Node with id '{node_id}' not found.")
                raise NodeNotFoundError(f"Node with id '{node_id}' not found.")
        except exceptions.Neo4jError as e:
            logger.error(f"Failed to update node: {e}")
            raise StorageError(f"Failed to update node: {e}")

    def delete_node(self, node_id: str) -> None:
        """
        Deletes a node from the graph.

        Args:
            node_id (str): Unique identifier of the node.

        Raises:
            NodeNotFoundError: If the node does not exist.
            StorageError: If there is an issue deleting the node.
        """
        cypher = "MATCH (n {id: $node_id}) DETACH DELETE n RETURN COUNT(n) AS count"
        params = {'node_id': node_id}
        try:
            result = self.session.run(cypher, params)
            record = result.single()
            if record and record['count'] > 0:
                logger.info(f"Node with id '{node_id}' deleted.")
            else:
                logger.warning(f"Node with id '{node_id}' not found.")
                raise NodeNotFoundError(f"Node with id '{node_id}' not found.")
        except exceptions.Neo4jError as e:
            logger.error(f"Failed to delete node: {e}")
            raise StorageError(f"Failed to delete node: {e}")

    def delete_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str
    ) -> None:
        """
        Deletes a specific relationship between two nodes.

        Args:
            source_id (str): Unique identifier of the source node.
            target_id (str): Unique identifier of the target node.
            relationship (str): Type of the relationship to delete.

        Raises:
            StorageError: If there is an issue deleting the relationship.
        """
        cypher = (
            "MATCH (a {id: $source_id})-[r:%s]->(b {id: $target_id}) "
            "DELETE r"
        ) % relationship
        params = {
            'source_id': source_id,
            'target_id': target_id
        }
        try:
            result = self.session.run(cypher, params)
            if result.consume().counters.relationships_deleted == 0:
                logger.warning(f"No relationship '{relationship}' found between '{source_id}' and '{target_id}'.")
                raise StorageError(f"Relationship '{relationship}' between '{source_id}' and '{target_id}' not found.")
            logger.info(f"Relationship '{relationship}' between '{source_id}' and '{target_id}' deleted.")
        except exceptions.Neo4jError as e:
            logger.error(f"Failed to delete relationship: {e}")
            raise StorageError(f"Failed to delete relationship: {e}")

    def update_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        properties: Dict[str, Any]
    ) -> None:
        """
        Updates properties of a specific relationship between two nodes.

        Args:
            source_id (str): Unique identifier of the source node.
            target_id (str): Unique identifier of the target node.
            relationship (str): Type of the relationship to update.
            properties (Dict[str, Any]): Properties to update on the relationship.

        Raises:
            StorageError: If there is an issue updating the relationship.
        """
        cypher = (
            "MATCH (a {id: $source_id})-[r:%s]->(b {id: $target_id}) "
            "SET r += $properties RETURN r"
        ) % relationship
        params = {
            'source_id': source_id,
            'target_id': target_id,
            'properties': properties
        }
        try:
            result = self.session.run(cypher, params)
            record = result.single()
            if record:
                logger.info(f"Relationship '{relationship}' between '{source_id}' and '{target_id}' updated with properties {properties}.")
            else:
                logger.warning(f"Relationship '{relationship}' between '{source_id}' and '{target_id}' not found.")
                raise StorageError(f"Relationship '{relationship}' between '{source_id}' and '{target_id}' not found.")
        except exceptions.Neo4jError as e:
            logger.error(f"Failed to update relationship: {e}")
            raise StorageError(f"Failed to update relationship: {e}")

    def get_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship: str
    ) -> Dict[str, Any]:
        """
        Retrieves a specific relationship between two nodes.

        Args:
            source_id (str): Unique identifier of the source node.
            target_id (str): Unique identifier of the target node.
            relationship (str): Type of the relationship to retrieve.

        Returns:
            Dict[str, Any]: A dictionary containing the relationship's properties.

        Raises:
            StorageError: If there is an issue retrieving the relationship.
        """
        cypher = (
            "MATCH (a {id: $source_id})-[r:%s]->(b {id: $target_id}) "
            "RETURN r"
        ) % relationship
        params = {
            'source_id': source_id,
            'target_id': target_id
        }
        try:
            result = self.session.run(cypher, params)
            record = result.single()
            if record:
                relationship_data = record['r']
                properties = dict(relationship_data)
                properties['type'] = relationship.type  # Include relationship type
                logger.info(f"Relationship '{relationship}' between '{source_id}' and '{target_id}' retrieved.")
                return properties
            else:
                logger.warning(f"Relationship '{relationship}' between '{source_id}' and '{target_id}' not found.")
                raise StorageError(f"Relationship '{relationship}' between '{source_id}' and '{target_id}' not found.")
        except exceptions.Neo4jError as e:
            logger.error(f"Failed to retrieve relationship: {e}")
            raise StorageError(f"Failed to retrieve relationship: {e}")

    def delete_all_edges(self) -> None:
        """
        Deletes all relationships from the Neo4j graph database without deleting nodes.

        Raises:
            StorageError: If there is an issue deleting relationships.
        """
        cypher = "MATCH ()-[r]->() DELETE r"
        try:
            self.session.run(cypher)
            logger.info("All relationships have been deleted from Neo4j.")
        except exceptions.Neo4jError as e:
            logger.error(f"Failed to delete all relationships: {e}")
            raise StorageError(f"Failed to delete all relationships: {e}")

    def delete_relationships_by_type(self, relationship: str) -> None:
        """
        Deletes all relationships of a specific type from the Neo4j graph database.

        Args:
            relationship (str): The type of relationships to delete.

        Raises:
            StorageError: If there is an issue deleting the relationships.
        """
        cypher = f"MATCH ()-[r:{relationship}]->() DELETE r"
        try:
            self.session.run(cypher)
            logger.info(f"All relationships of type '{relationship}' have been deleted from Neo4j.")
        except exceptions.Neo4jError as e:
            logger.error(f"Failed to delete relationships of type '{relationship}': {e}")
            raise StorageError(f"Failed to delete relationships of type '{relationship}': {e}")

    def delete_all(self) -> None:
        """
        Deletes all nodes and relationships from the Neo4j graph database.

        Raises:
            StorageError: If there is an issue deleting all nodes and relationships.
        """
        cypher = "MATCH (n) DETACH DELETE n"
        try:
            self.session.run(cypher)
            logger.info("All nodes and relationships have been deleted from Neo4j.")
        except exceptions.Neo4jError as e:
            logger.error(f"Failed to delete all nodes and relationships: {e}")
            raise StorageError(f"Failed to delete all nodes and relationships: {e}")

    def get_neighbors(
        self,
        node_id: str,
        relationship: Optional[str] = None,
        direction: str = "both"
    ) -> List[Dict[str, Any]]:
        """
        Retrieves neighboring nodes connected by edges.

        Args:
            node_id (str): Unique identifier of the node.
            relationship (Optional[str]): Filter by relationship type.
            direction (str): Direction of the relationships ('in', 'out', 'both').

        Returns:
            List[Dict[str, Any]]: A list of neighboring nodes.

        Raises:
            NodeNotFoundError: If the node does not exist.
            StorageError: If there is an issue retrieving neighbors.
        """
        if direction not in ["in", "out", "both"]:
            raise ValueError("Invalid direction. Must be 'in', 'out', or 'both'.")

        rel_type = f":{relationship}" if relationship else ''
        if direction == "in":
            pattern = f"<-[r{rel_type}]-"
        elif direction == "out":
            pattern = f"-[r{rel_type}]->"
        else:  # both
            pattern = f"-[r{rel_type}]-"

        cypher = f"MATCH (n {{id: $node_id}}){pattern}(neighbor) RETURN neighbor"
        params = {'node_id': node_id}
        try:
            # First, check if the node exists
            node_exists_query = "MATCH (n {id: $node_id}) RETURN n"
            node_result = self.session.run(node_exists_query, params)
            if not node_result.single():
                logger.warning(f"Node with id '{node_id}' not found.")
                raise NodeNotFoundError(f"Node with id '{node_id}' not found.")
            # Get neighbors
            result = self.session.run(cypher, params)
            neighbors = []
            for record in result:
                node = record['neighbor']
                neighbor_data = {
                    'id': node['id'],
                    'properties': {k: v for k, v in node.items() if k != 'id'},
                    'labels': list(node.labels)
                }
                neighbors.append(neighbor_data)
            logger.info(f"Neighbors of node '{node_id}' retrieved.")
            return neighbors
        except NodeNotFoundError:
            raise
        except exceptions.Neo4jError as e:
            logger.error(f"Failed to get neighbors: {e}")
            raise StorageError(f"Failed to get neighbors: {e}")

    def query_nodes(
        self,
        properties: Dict[str, Any],
        labels: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Queries nodes based on properties and labels.

        Args:
            properties (Dict[str, Any]): Properties to filter nodes.
            labels (Optional[List[str]]): Labels to filter nodes.

        Returns:
            List[Dict[str, Any]]: A list of nodes matching the query.

        Raises:
            StorageError: If there is an issue querying nodes.
        """
        labels_str = ':' + ':'.join(labels) if labels else ''
        params = {}
        cypher = f"MATCH (n{labels_str})"

        if properties:
            props_conditions = ' AND '.join([f"n.{key} = ${key}" for key in properties.keys()])
            cypher += f" WHERE {props_conditions}"
            params.update(properties)

        cypher += " RETURN n"

        try:
            result = self.session.run(cypher, params)
            nodes = []
            for record in result:
                node = record['n']
                node_data = {
                    'id': node['id'],
                    'properties': {k: v for k, v in node.items() if k != 'id'},
                    'labels': list(node.labels)
                }
                nodes.append(node_data)
            logger.info(f"Query returned {len(nodes)} nodes.")
            return nodes
        except exceptions.Neo4jError as e:
            logger.error(f"Failed to query nodes: {e}")
            raise StorageError(f"Failed to query nodes: {e}")

    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """
        Executes a raw query against the graph database.

        Args:
            query (str): The query string.
            parameters (Optional[Dict[str, Any]]): Parameters for parameterized queries.

        Returns:
            Any: The result of the query.

        Raises:
            StorageError: If there is an issue executing the query.
        """
        try:
            result = self.session.run(query, parameters)
            records = [record.data() for record in result]
            logger.info(f"Executed query: {query}")
            return records
        except exceptions.Neo4jError as e:
            logger.error(f"Failed to execute query: {e}")
            raise StorageError(f"Failed to execute query: {e}")

    def close(self) -> None:
        """
        Closes the graph database connection and releases resources.
        """
        if hasattr(self, 'session') and self.session:
            self.session.close()
        if hasattr(self, 'driver') and self.driver:
            self.driver.close()
        logger.info("Closed connection to Neo4j database.")

    def __del__(self):
        """Destructor to ensure resources are cleaned up."""
        self.close()