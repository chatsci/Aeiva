# weaviate_vector_store.py

import logging
from typing import Any, Dict, List, Optional

from aeiva.storage.vector_database import VectorDatabase

try:
    import weaviate
    from weaviate.client import Client
    from weaviate.auth import AuthApiKey, AuthClientPassword
    from weaviate.exceptions import WeaviateException
except ImportError:
    raise ImportError("The 'weaviate-client' library is required. Install it using 'pip install weaviate-client'.")

logger = logging.getLogger(__name__)


class WeaviateDatabase(VectorDatabase):
    """
    Concrete implementation of VectorStoreBase using Weaviate.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the Weaviate vector store.

        Args:
            config (Dict[str, Any]): Configuration dictionary.
        """
        self.config = config
        self.url = config.get('url', 'http://localhost:8080')
        self.api_key = config.get('api_key')
        self.auth_client_secret = config.get('auth_client_secret')
        self.timeout_config = config.get('timeout_config', (2, 20))
        self.additional_headers = config.get('additional_headers')
        self.embedding_model = config.get('embedding_model')
        self.index_name = config.get('index_name', 'MyIndex')
        self.vector_dim = config.get('vector_dim', 512)
        self.distance_metric = config.get('distance_metric', 'cosine')

        self.client = self.create_client()
        self.create_index(
            index_name=self.index_name,
            vector_dim=self.vector_dim,
            distance_metric=self.distance_metric
        )

    def create_client(self) -> Client:
        """
        Initializes the client connection to the Weaviate vector store.

        Returns:
            Client: The Weaviate client instance.

        Raises:
            ConnectionError: If the client fails to connect to the Weaviate instance.
        """
        try:
            if self.api_key:
                auth_config = AuthApiKey(api_key=self.api_key)
            elif self.auth_client_secret:
                auth_config = AuthClientPassword(**self.auth_client_secret)
            else:
                auth_config = None

            client = weaviate.Client(
                url=self.url,
                auth_client_secret=auth_config,
                timeout_config=self.timeout_config,
                additional_headers=self.additional_headers
            )

            if not client.is_ready():
                raise ConnectionError(f"Weaviate at {self.url} is not ready.")

            logger.info(f"Connected to Weaviate at {self.url}.")
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            raise ConnectionError(f"Failed to connect to Weaviate: {e}")

    def create_index(self, index_name: str, vector_dim: int, distance_metric: str) -> None:
        """
        Create a new index (class) in Weaviate.

        Args:
            index_name (str): The name of the index.
            vector_dim (int): The dimensionality of the vectors.
            distance_metric (str): The distance metric to use.

        Raises:
            WeaviateException: If there is an issue creating the index.
        """
        try:
            if self.client.schema.contains(index_name):
                logger.info(f"Index {index_name} already exists. Skipping creation.")
                return

            class_obj = {
                "class": index_name,
                "vectorizer": "none",
                "vectorIndexType": "hnsw",
                "vectorIndexConfig": {
                    "distance": distance_metric
                },
                "properties": [
                    {
                        "name": "id",
                        "dataType": ["string"],
                        "description": "Unique identifier",
                    },
                    {
                        "name": "payload",
                        "dataType": ["blob"],
                        "description": "Payload data",
                    },
                ]
            }

            self.client.schema.create_class(class_obj)
            logger.info(f"Index {index_name} created successfully.")
        except WeaviateException as e:
            logger.error(f"Failed to create index: {e}")
            raise

    def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """
        Insert vectors into the collection.

        Args:
            collection_name (str): The name of the collection (index).
            vectors (List[List[float]]): A list of vectors to insert.
            payloads (Optional[List[Dict[str, Any]]]): Optional metadata associated with each vector.
            ids (Optional[List[str]]): Optional unique identifiers for each vector.

        Raises:
            ValueError: If input data is invalid.
            WeaviateException: If there is an issue inserting vectors.
        """
        if collection_name != self.index_name:
            raise ValueError("Collection name does not match initialized index name.")

        if ids is None:
            raise ValueError("Weaviate requires IDs to be provided for each vector.")

        if payloads is None:
            payloads = [{} for _ in range(len(vectors))]

        if not (len(ids) == len(vectors) == len(payloads)):
            raise ValueError("Lengths of ids, vectors, and payloads must be equal.")

        try:
            with self.client.batch(batch_size=100) as batch:
                for id_, vector, payload in zip(ids, vectors, payloads):
                    data_object = {
                        "id": id_,
                        "payload": payload
                    }
                    batch.add_data_object(
                        data_object=data_object,
                        class_name=collection_name,
                        vector=vector
                    )
            logger.info(f"Inserted {len(vectors)} vectors into index {collection_name}.")
        except WeaviateException as e:
            logger.error(f"Failed to insert vectors: {e}")
            raise

    def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in the collection.

        Args:
            collection_name (str): The name of the collection (index).
            query_vector (List[float]): The vector to search with.
            top_k (int): The number of top results to return.
            filters (Optional[Dict[str, Any]]): Optional filters to apply to the search.

        Returns:
            List[Dict[str, Any]]: A list of search results.

        Raises:
            ValueError: If collection name does not match.
            WeaviateException: If there is an issue performing the search.
        """
        if collection_name != self.index_name:
            raise ValueError("Collection name does not match initialized index name.")

        try:
            near_vector = {
                "vector": query_vector,
            }

            where_filter = self._build_filters(filters)

            result = self.client.query.get(
                class_name=collection_name,
                properties=["id", "payload"]
            ).with_near_vector(near_vector).with_where(where_filter).with_limit(top_k).do()

            output = []
            for item in result["data"]["Get"][collection_name]:
                result_item = {
                    "id": item["id"],
                    "score": item["_additional"]["certainty"],  # or distance
                    "payload": item["payload"]
                }
                output.append(result_item)
            return output
        except WeaviateException as e:
            logger.error(f"Failed to search vectors: {e}")
            raise

    def _build_filters(self, filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Build a Weaviate where filter from a dictionary.

        Args:
            filters (Optional[Dict[str, Any]]): Filters to apply.

        Returns:
            Optional[Dict[str, Any]]: A Weaviate where filter.
        """
        if not filters:
            return None

        conditions = []
        for key, value in filters.items():
            condition = {
                "path": [key],
                "operator": "Equal",
                "valueString": value if isinstance(value, str) else None,
                "valueInt": value if isinstance(value, int) else None,
                "valueBoolean": value if isinstance(value, bool) else None,
                "valueNumber": value if isinstance(value, float) else None,
            }
            conditions.append(condition)

        where_filter = {
            "operator": "And",
            "operands": conditions
        }

        return where_filter

    def delete_vector(self, collection_name: str, vector_id: str) -> None:
        """
        Delete a vector from the collection by its ID.

        Args:
            collection_name (str): The name of the collection (index).
            vector_id (str): The unique identifier of the vector to delete.

        Raises:
            ValueError: If collection name does not match.
            WeaviateException: If there is an issue deleting the vector.
        """
        if collection_name != self.index_name:
            raise ValueError("Collection name does not match initialized index name.")

        try:
            self.client.data_object.delete(
                uuid=vector_id,
                class_name=collection_name
            )
            logger.info(f"Deleted vector with ID {vector_id} from index {collection_name}.")
        except WeaviateException as e:
            logger.error(f"Failed to delete vector: {e}")
            raise

    def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: Optional[List[float]] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update a vector's data or payload.

        Args:
            collection_name (str): The name of the collection (index).
            vector_id (str): The unique identifier of the vector to update.
            vector (Optional[List[float]]): The new vector data.
            payload (Optional[Dict[str, Any]]): The new payload data.

        Raises:
            ValueError: If collection name does not match.
            WeaviateException: If there is an issue updating the vector.
        """
        if collection_name != self.index_name:
            raise ValueError("Collection name does not match initialized index name.")

        try:
            data_object = {}
            if payload is not None:
                data_object["payload"] = payload

            self.client.data_object.update(
                data_object=data_object,
                class_name=collection_name,
                uuid=vector_id,
                vector=vector
            )
            logger.info(f"Updated vector with ID {vector_id} in index {collection_name}.")
        except WeaviateException as e:
            logger.error(f"Failed to update vector: {e}")
            raise

    def get_vector(self, collection_name: str, vector_id: str) -> Dict[str, Any]:
        """
        Retrieve a vector by its ID.

        Args:
            collection_name (str): The name of the collection (index).
            vector_id (str): The unique identifier of the vector.

        Returns:
            Dict[str, Any]: A dictionary containing the vector data and payload.

        Raises:
            ValueError: If collection name does not match.
            KeyError: If the vector is not found.
            WeaviateException: If there is an issue retrieving the vector.
        """
        if collection_name != self.index_name:
            raise ValueError("Collection name does not match initialized index name.")

        try:
            result = self.client.data_object.get_by_id(
                uuid=vector_id,
                class_name=collection_name,
                additional_properties=["vector"]
            )
            if result is None:
                raise KeyError(f"Vector with ID {vector_id} not found in index {collection_name}.")

            vector_data = {
                "id": result["id"],
                "vector": result["vector"],
                "payload": result["payload"]
            }
            return vector_data
        except WeaviateException as e:
            logger.error(f"Failed to retrieve vector: {e}")
            raise

    def list_collections(self) -> List[str]:
        """
        List all available indexes (classes).

        Returns:
            List[str]: A list of index names.
        """
        try:
            schema = self.client.schema.get()
            return [clazz["class"] for clazz in schema["classes"]]
        except WeaviateException as e:
            logger.error(f"Failed to list collections: {e}")
            raise

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete an entire index (class).

        Args:
            collection_name (str): The name of the collection (index) to delete.

        Raises:
            WeaviateException: If there is an issue deleting the collection.
        """
        try:
            self.client.schema.delete_class(collection_name)
            logger.info(f"Deleted index {collection_name}.")
        except WeaviateException as e:
            logger.error(f"Failed to delete collection: {e}")
            raise

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get information about a collection (index).

        Args:
            collection_name (str): The name of the collection (index).

        Returns:
            Dict[str, Any]: Information about the collection.

        Raises:
            WeaviateException: If there is an issue retrieving the collection info.
        """
        try:
            class_schema = self.client.schema.get(class_name=collection_name)
            return class_schema
        except WeaviateException as e:
            logger.error(f"Failed to get collection info: {e}")
            raise

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("Closed connection to Weaviate.")