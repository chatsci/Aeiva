import logging
from typing import List, Dict, Any, Optional
from aeiva.storage.vector_database import VectorDatabase

try:
    from pymilvus import (
        connections,
        Collection,
        CollectionSchema,
        FieldSchema,
        DataType,
        utility,
        MilvusException,
    )
except ImportError:
    raise ImportError("The 'pymilvus' library is required. Please install it using 'pip install pymilvus'.")

logger = logging.getLogger(__name__)


class MilvusDatabase(VectorDatabase):
    """
    Concrete implementation of VectorStoreBase using Milvus.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the Milvus vector store.

        Args:
            config (Dict[str, Any]): Configuration dictionary.
        """
        self.config = config
        self.collection_name = config.get('collection_name')
        self.uri = config.get('uri')
        self.user = config.get('user')
        self.password = config.get('password')
        self.token = config.get('token')
        self.embedding_model_dims = config.get('embedding_model_dims')
        self.metric_type = config.get('metric_type', 'L2')  # Default to 'L2' metric

        if not all([self.collection_name, self.uri, self.embedding_model_dims]):
            raise ValueError("Required configuration parameters are missing.")

        self.create_client(
            uri=self.uri,
            user=self.user,
            password=self.password,
            token=self.token
        )
        self.create_collection(
            collection_name=self.collection_name,
            vector_size=self.embedding_model_dims,
            distance_metric=self.metric_type
        )

    def create_client(
        self,
        uri: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
        token: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Initializes the client connection to the Milvus vector store.

        Args:
            uri (str): The URI of the vector store instance.
            user (Optional[str]): Username for authentication.
            password (Optional[str]): Password for authentication.
            token (Optional[str]): Access token for authentication.
            **kwargs: Additional parameters.
        """
        try:
            connections.connect(
                alias="default",
                uri=uri,
                user=user,
                password=password,
                token=token,
                **kwargs
            )
            logger.info(f"Connected to Milvus at {uri}.")
        except MilvusException as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise ConnectionError(f"Failed to connect to Milvus: {e}")

    def create_collection(self, collection_name: str, vector_size: int, distance_metric: str) -> None:
        """
        Create a new vector collection in Milvus.

        Args:
            collection_name (str): The name of the collection.
            vector_size (int): The dimensionality of the vectors.
            distance_metric (str): The distance metric to use (e.g., 'L2', 'IP', 'COSINE').
        """
        if utility.has_collection(collection_name):
            logger.info(f"Collection {collection_name} already exists. Skipping creation.")
            self.collection = Collection(collection_name)
            return

        # Define the schema
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=64),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=vector_size),
            FieldSchema(name="payload", dtype=DataType.JSON)
        ]
        schema = CollectionSchema(fields=fields, description="Milvus Vector Store Collection")

        # Create the collection
        self.collection = Collection(name=collection_name, schema=schema)
        logger.info(f"Collection {collection_name} created successfully.")

        # Create index
        index_params = {
            "metric_type": distance_metric,
            "index_type": "AUTOINDEX",
            "params": {}
        }
        self.collection.create_index(field_name="vector", index_params=index_params)
        logger.info(f"Index created on collection {collection_name}.")

    def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """
        Insert vectors into a collection.

        Args:
            collection_name (str): The name of the collection.
            vectors (List[List[float]]): A list of vectors to insert.
            payloads (Optional[List[Dict[str, Any]]]): Optional metadata associated with each vector.
            ids (Optional[List[str]]): Optional unique identifiers for each vector.
        """
        if collection_name != self.collection_name:
            raise ValueError("Collection name does not match initialized collection name.")

        if ids is None:
            raise ValueError("Milvus requires IDs to be provided for each vector.")
        if payloads is None:
            payloads = [{} for _ in range(len(vectors))]
        if not (len(ids) == len(vectors) == len(payloads)):
            raise ValueError("Lengths of ids, vectors, and payloads must be equal.")

        data = [
            ids,
            vectors,
            payloads
        ]
        self.collection.insert(data)
        logger.info(f"Inserted {len(vectors)} vectors into collection {collection_name}.")

    def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in a collection.

        Args:
            collection_name (str): The name of the collection.
            query_vector (List[float]): The vector to search with.
            top_k (int): The number of top results to return.
            filters (Optional[Dict[str, Any]]): Optional filters to apply to the search.

        Returns:
            List[Dict[str, Any]]: A list of search results.
        """
        if collection_name != self.collection_name:
            raise ValueError("Collection name does not match initialized collection name.")

        search_params = {
            "metric_type": self.metric_type,
            "params": {}
        }

        expr = self._build_filter_expression(filters)
        results = self.collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["id", "payload"]
        )

        output = []
        for hits in results:
            for hit in hits:
                result = {
                    'id': hit.entity.get('id'),
                    'score': hit.distance,
                    'payload': hit.entity.get('payload')
                }
                output.append(result)
        return output

    def _build_filter_expression(self, filters: Optional[Dict[str, Any]]) -> str:
        """
        Build an expression string for filtering in Milvus.

        Args:
            filters (Optional[Dict[str, Any]]): Filters to apply.

        Returns:
            str: The expression string.
        """
        if not filters:
            return ""

        expressions = []
        for key, value in filters.items():
            if isinstance(value, str):
                expressions.append(f'payload["{key}"] == "{value}"')
            else:
                expressions.append(f'payload["{key}"] == {value}')
        expr = " and ".join(expressions)
        return expr

    def delete_vector(self, collection_name: str, vector_id: str) -> None:
        """
        Delete a vector from a collection by its ID.

        Args:
            collection_name (str): The name of the collection.
            vector_id (str): The unique identifier of the vector to delete.
        """
        if collection_name != self.collection_name:
            raise ValueError("Collection name does not match initialized collection name.")

        expr = f'id == "{vector_id}"'
        self.collection.delete(expr)
        logger.info(f"Deleted vector with ID {vector_id} from collection {collection_name}.")

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
            collection_name (str): The name of the collection.
            vector_id (str): The unique identifier of the vector to update.
            vector (Optional[List[float]]): The new vector data.
            payload (Optional[Dict[str, Any]]): The new payload data.
        """
        if collection_name != self.collection_name:
            raise ValueError("Collection name does not match initialized collection name.")

        # Milvus doesn't support direct updates; need to delete and re-insert
        # Fetch existing vector and payload
        expr = f'id == "{vector_id}"'
        results = self.collection.query(expr=expr, output_fields=["vector", "payload"])

        if not results:
            raise KeyError(f"Vector with ID {vector_id} not found in collection {collection_name}.")

        existing_vector = results[0]['vector']
        existing_payload = results[0]['payload']

        new_vector = vector if vector is not None else existing_vector
        new_payload = payload if payload is not None else existing_payload

        # Delete the existing vector
        self.collection.delete(expr)

        # Re-insert with updated data
        self.insert_vectors(
            collection_name=collection_name,
            vectors=[new_vector],
            payloads=[new_payload],
            ids=[vector_id]
        )
        logger.info(f"Updated vector with ID {vector_id} in collection {collection_name}.")

    def get_vector(self, collection_name: str, vector_id: str) -> Dict[str, Any]:
        """
        Retrieve a vector by its ID.

        Args:
            collection_name (str): The name of the collection.
            vector_id (str): The unique identifier of the vector.

        Returns:
            Dict[str, Any]: A dictionary containing the vector data and payload.
        """
        if collection_name != self.collection_name:
            raise ValueError("Collection name does not match initialized collection name.")

        expr = f'id == "{vector_id}"'
        results = self.collection.query(expr=expr, output_fields=["vector", "payload"])

        if not results:
            raise KeyError(f"Vector with ID {vector_id} not found in collection {collection_name}.")

        vector_data = {
            'id': vector_id,
            'vector': results[0]['vector'],
            'payload': results[0]['payload']
        }
        return vector_data

    def list_collections(self) -> List[str]:
        """
        List all available vector collections.

        Returns:
            List[str]: A list of collection names.
        """
        return utility.list_collections()

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete an entire vector collection.

        Args:
            collection_name (str): The name of the collection to delete.
        """
        self.collection.drop()
        logger.info(f"Deleted collection {collection_name}.")

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get information about a collection.

        Args:
            collection_name (str): The name of the collection.

        Returns:
            Dict[str, Any]: Information about the collection.
        """
        if collection_name != self.collection_name:
            raise ValueError("Collection name does not match initialized collection name.")

        info = self.collection.describe()
        return info

    def __del__(self):
        """Clean up resources."""
        connections.disconnect("default")