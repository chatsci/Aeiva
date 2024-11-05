import logging
from typing import List, Dict, Any, Optional
from aeiva.storage.vector_database import VectorDatabase

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    raise ImportError("The 'chromadb' library is required. Please install it using 'pip install chromadb'.")

logger = logging.getLogger(__name__)


class ChromaDatabase(VectorDatabase):
    """
    Concrete implementation of VectorStoreBase using ChromaDB.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the ChromaDB vector store.

        Args:
            config (Dict[str, Any]): Configuration dictionary.
        """
        self.config = config
        self.collection_name = config.get('collection_name')
        self.client = config.get('client')
        self.host = config.get('host')
        self.port = config.get('port')
        self.path = config.get('path')

        if not self.collection_name:
            raise ValueError("Collection name must be provided in the configuration.")

        self.create_client(
            host=self.host,
            port=self.port,
            path=self.path
        )
        self.create_collection(
            collection_name=self.collection_name,
            vector_size=None,  # ChromaDB does not require specifying vector size upfront
            distance_metric='cosine'
        )

    def create_client(
        self,
        uri: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        path: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Initializes the client connection to the vector store.

        Args:
            uri (Optional[str]): Not used for ChromaDB.
            host (Optional[str]): Host address for ChromaDB server.
            port (Optional[int]): Port for ChromaDB server.
            path (Optional[str]): Path to the database directory.
            **kwargs: Additional parameters.
        """
        if self.client:
            return  # Client already provided

        settings = Settings(anonymized_telemetry=False)

        if host and port:
            settings.chroma_api_impl = "chromadb.api.fastapi.FastAPI"
            settings.chroma_server_host = host
            settings.chroma_server_http_port = port
        else:
            if not path:
                path = "db"
            settings.persist_directory = path
            settings.is_persistent = True

        self.client = chromadb.Client(settings)
        logger.info("ChromaDB client initialized.")

    def create_collection(self, collection_name: str, vector_size: int, distance_metric: str) -> None:
        """
        Create a new vector collection in ChromaDB.

        Args:
            collection_name (str): The name of the collection.
            vector_size (int): Not used for ChromaDB.
            distance_metric (str): Not used for ChromaDB.
        """
        # Check if collection exists
        existing_collections = self.list_collections()
        if collection_name in existing_collections:
            logger.info(f"Collection {collection_name} already exists. Skipping creation.")
            self.collection = self.client.get_collection(name=collection_name)
        else:
            self.collection = self.client.create_collection(name=collection_name)
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
            ids = [str(i) for i in range(len(vectors))]
        if payloads is None:
            payloads = [{} for _ in range(len(vectors))]
        if not (len(ids) == len(vectors) == len(payloads)):
            raise ValueError("Lengths of ids, vectors, and payloads must be equal.")

        self.collection.add(ids=ids, embeddings=vectors, metadatas=payloads)
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

        results = self.collection.query(
            query_embeddings=[query_vector],
            where=filters,
            n_results=top_k
        )
        # Parse the results
        output = []
        for idx, (ids, distances, metadatas) in enumerate(zip(results['ids'], results['distances'], results['metadatas'])):
            for i in range(len(ids)):
                result = {
                    'id': ids[i],
                    'score': distances[i],
                    'payload': metadatas[i]
                }
                output.append(result)
        return output

    def delete_vector(self, collection_name: str, vector_id: str) -> None:
        """
        Delete a vector from a collection by its ID.

        Args:
            collection_name (str): The name of the collection.
            vector_id (str): The unique identifier of the vector to delete.
        """
        if collection_name != self.collection_name:
            raise ValueError("Collection name does not match initialized collection name.")

        self.collection.delete(ids=[vector_id])
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

        self.collection.update(ids=[vector_id], embeddings=[vector] if vector else None, metadatas=[payload] if payload else None)
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

        result = self.collection.get(ids=[vector_id])
        if not result['ids']:
            raise KeyError(f"Vector with ID {vector_id} not found in collection {collection_name}.")

        vector_data = {
            'id': result['ids'][0],
            'vector': result['embeddings'][0] if 'embeddings' in result else None,
            'payload': result['metadatas'][0]
        }
        return vector_data

    def list_collections(self) -> List[str]:
        """
        List all available vector collections.

        Returns:
            List[str]: A list of collection names.
        """
        collections = self.client.list_collections()
        return [collection.name for collection in collections]

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete an entire vector collection.

        Args:
            collection_name (str): The name of the collection to delete.
        """
        self.client.delete_collection(name=collection_name)
        logger.info(f"Deleted collection {collection_name}.")

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get information about a collection.

        Args:
            collection_name (str): The name of the collection.

        Returns:
            Dict[str, Any]: Information about the collection.
        """
        collection = self.client.get_collection(name=collection_name)
        return {
            'name': collection.name,
            'metadata': collection.metadata
        }