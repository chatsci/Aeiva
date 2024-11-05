import logging
from typing import List, Dict, Any, Optional
from aeiva.storage.vector_database import VectorDatabase

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import (
        VectorParams,
        Distance,
        PointStruct,
        Filter,
        FieldCondition,
        MatchValue,
    )
except ImportError:
    raise ImportError("The 'qdrant-client' library is required. Please install it using 'pip install qdrant-client'.")

logger = logging.getLogger(__name__)


class QdrantDatabase(VectorDatabase):
    """
    Concrete implementation of VectorStoreBase using Qdrant.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the Qdrant vector store.

        Args:
            config (Dict[str, Any]): Configuration dictionary.
        """
        self.config = config
        self.collection_name = config.get('collection_name')
        self.embedding_model_dims = config.get('embedding_model_dims')
        self.client = config.get('client')
        self.host = config.get('host')
        self.port = config.get('port')
        self.path = config.get('path')
        self.url = config.get('url')
        self.api_key = config.get('api_key')
        self.on_disk = config.get('on_disk', False)

        if not all([self.collection_name, self.embedding_model_dims]):
            raise ValueError("Required configuration parameters are missing.")

        self.create_client()
        self.create_collection(
            collection_name=self.collection_name,
            vector_size=self.embedding_model_dims,
            distance_metric='COSINE'
        )

    def create_client(self, **kwargs) -> None:
        """
        Initializes the client connection to the Qdrant vector store.

        Args:
            **kwargs: Additional parameters.
        """
        if self.client:
            return  # Client already provided

        client_params = {}
        if self.api_key:
            client_params['api_key'] = self.api_key
        if self.url:
            client_params['url'] = self.url
        elif self.host and self.port:
            client_params['host'] = self.host
            client_params['port'] = self.port
        else:
            client_params['path'] = self.path

        self.client = QdrantClient(**client_params)
        logger.info("Qdrant client initialized.")

    def create_collection(self, collection_name: str, vector_size: int, distance_metric: str) -> None:
        """
        Create a new vector collection in Qdrant.

        Args:
            collection_name (str): The name of the collection.
            vector_size (int): The dimensionality of the vectors.
            distance_metric (str): The distance metric to use (e.g., 'COSINE').
        """
        # Check if collection exists
        collections = self.list_collections()
        if collection_name in collections:
            logger.info(f"Collection {collection_name} already exists. Skipping creation.")
            return

        vector_params = VectorParams(
            size=vector_size,
            distance=getattr(Distance, distance_metric.upper()),
            on_disk=self.on_disk
        )
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=vector_params
        )
        logger.info(f"Collection {collection_name} created successfully.")

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
            ids = [i for i in range(len(vectors))]
        if payloads is None:
            payloads = [{} for _ in range(len(vectors))]
        if not (len(ids) == len(vectors) == len(payloads)):
            raise ValueError("Lengths of ids, vectors, and payloads must be equal.")

        points = [
            PointStruct(
                id=id_,
                vector=vector,
                payload=payload
            )
            for id_, vector, payload in zip(ids, vectors, payloads)
        ]
        self.client.upsert(
            collection_name=collection_name,
            points=points
        )
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

        query_filter = self._build_filter(filters)
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=query_filter
        )

        output = []
        for hit in results:
            result = {
                'id': hit.id,
                'score': hit.score,
                'payload': hit.payload
            }
            output.append(result)
        return output

    def _build_filter(self, filters: Optional[Dict[str, Any]]) -> Optional[Filter]:
        """
        Build a Qdrant filter object from a dictionary.

        Args:
            filters (Optional[Dict[str, Any]]): Filters to apply.

        Returns:
            Optional[Filter]: A Qdrant Filter object.
        """
        if not filters:
            return None

        conditions = []
        for key, value in filters.items():
            conditions.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value)
                )
            )
        return Filter(must=conditions)

    def delete_vector(self, collection_name: str, vector_id: str) -> None:
        """
        Delete a vector from a collection by its ID.

        Args:
            collection_name (str): The name of the collection.
            vector_id (str): The unique identifier of the vector to delete.
        """
        if collection_name != self.collection_name:
            raise ValueError("Collection name does not match initialized collection name.")

        self.client.delete(
            collection_name=collection_name,
            points_selector=[vector_id]
        )
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

        point = PointStruct(
            id=vector_id,
            vector=vector,
            payload=payload
        )
        self.client.upsert(
            collection_name=collection_name,
            points=[point]
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

        result = self.client.retrieve(
            collection_name=collection_name,
            ids=[vector_id]
        )
        if not result:
            raise KeyError(f"Vector with ID {vector_id} not found in collection {collection_name}.")

        point = result[0]
        vector_data = {
            'id': point.id,
            'vector': point.vector,
            'payload': point.payload
        }
        return vector_data

    def list_collections(self) -> List[str]:
        """
        List all available vector collections.

        Returns:
            List[str]: A list of collection names.
        """
        collections = self.client.get_collections().collections
        return [collection.name for collection in collections]

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete an entire vector collection.

        Args:
            collection_name (str): The name of the collection to delete.
        """
        self.client.delete_collection(collection_name=collection_name)
        logger.info(f"Deleted collection {collection_name}.")

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get information about a collection.

        Args:
            collection_name (str): The name of the collection.

        Returns:
            Dict[str, Any]: Information about the collection.
        """
        info = self.client.get_collection(collection_name=collection_name)
        return info.dict()