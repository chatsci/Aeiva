from abc import ABC, abstractmethod
from typing import List, Any, Optional, Dict

class VectorDatabase(ABC):
    """
    Abstract base class for vector storage operations.
    """

    @abstractmethod
    def create_client(
        self,
        uri: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
        db_name: Optional[str] = None,
        token: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> None:
        """
        Initializes the client connection to the vector store.

        Args:
            uri (str): The URI of the vector store instance.
            user (Optional[str]): Username for authentication.
            password (Optional[str]): Password for authentication.
            db_name (Optional[str]): Name of the database.
            token (Optional[str]): Access token for authentication.
            timeout (Optional[float]): Timeout duration for operations.
            **kwargs: Additional implementation-specific parameters.

        Raises:
            ConnectionError: If the client fails to connect to the vector store.
        """
        pass

    @abstractmethod
    def create_collection(self, collection_name: str, vector_size: int, distance_metric: str) -> None:
        """
        Create a new vector collection.

        Args:
            collection_name (str): The name of the collection.
            vector_size (int): The dimensionality of the vectors.
            distance_metric (str): The distance metric to use (e.g., 'euclidean', 'cosine').

        Raises:
            CollectionAlreadyExistsError: If a collection with the given name already exists.
            StorageError: If there is an issue creating the collection.
        """
        pass

    @abstractmethod
    def insert_vectors(self, collection_name: str, vectors: List[List[float]], payloads: Optional[List[Dict[str, Any]]] = None, ids: Optional[List[str]] = None) -> None:
        """
        Insert vectors into a collection.

        Args:
            collection_name (str): The name of the collection.
            vectors (List[List[float]]): A list of vectors to insert.
            payloads (Optional[List[Dict[str, Any]]]): Optional metadata associated with each vector.
            ids (Optional[List[str]]): Optional unique identifiers for each vector.

        Raises:
            CollectionNotFoundError: If the specified collection does not exist.
            StorageError: If there is an issue inserting the vectors.
        """
        pass

    @abstractmethod
    def search_vectors(self, collection_name: str, query_vector: List[float], top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in a collection.

        Args:
            collection_name (str): The name of the collection.
            query_vector (List[float]): The vector to search with.
            top_k (int): The number of top results to return.
            filters (Optional[Dict[str, Any]]): Optional filters to apply to the search.

        Returns:
            List[Dict[str, Any]]: A list of search results, each containing the vector ID, score, and payload.

        Raises:
            CollectionNotFoundError: If the specified collection does not exist.
            StorageError: If there is an issue performing the search.
        """
        pass

    @abstractmethod
    def delete_vector(self, collection_name: str, vector_id: str) -> None:
        """
        Delete a vector from a collection by its ID.

        Args:
            collection_name (str): The name of the collection.
            vector_id (str): The unique identifier of the vector to delete.

        Raises:
            CollectionNotFoundError: If the specified collection does not exist.
            VectorNotFoundError: If the vector with the specified ID does not exist.
            StorageError: If there is an issue deleting the vector.
        """
        pass

    @abstractmethod
    def update_vector(self, collection_name: str, vector_id: str, vector: Optional[List[float]] = None, payload: Optional[Dict[str, Any]] = None) -> None:
        """
        Update a vector's data or payload.

        Args:
            collection_name (str): The name of the collection.
            vector_id (str): The unique identifier of the vector to update.
            vector (Optional[List[float]]): The new vector data.
            payload (Optional[Dict[str, Any]]): The new payload data.

        Raises:
            CollectionNotFoundError: If the specified collection does not exist.
            VectorNotFoundError: If the vector with the specified ID does not exist.
            StorageError: If there is an issue updating the vector.
        """
        pass

    @abstractmethod
    def get_vector(self, collection_name: str, vector_id: str) -> Dict[str, Any]:
        """
        Retrieve a vector by its ID.

        Args:
            collection_name (str): The name of the collection.
            vector_id (str): The unique identifier of the vector.

        Returns:
            Dict[str, Any]: A dictionary containing the vector data and payload.

        Raises:
            CollectionNotFoundError: If the specified collection does not exist.
            VectorNotFoundError: If the vector with the specified ID does not exist.
            StorageError: If there is an issue retrieving the vector.
        """
        pass

    @abstractmethod
    def list_collections(self) -> List[str]:
        """
        List all available vector collections.

        Returns:
            List[str]: A list of collection names.

        Raises:
            StorageError: If there is an issue retrieving the collection list.
        """
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        """
        Delete an entire vector collection.

        Args:
            collection_name (str): The name of the collection to delete.

        Raises:
            CollectionNotFoundError: If the specified collection does not exist.
            StorageError: If there is an issue deleting the collection.
        """
        pass

    @abstractmethod
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get information about a collection.

        Args:
            collection_name (str): The name of the collection.

        Returns:
            Dict[str, Any]: Information about the collection, such as vector size and distance metric.

        Raises:
            CollectionNotFoundError: If the specified collection does not exist.
            StorageError: If there is an issue retrieving the collection information.
        """
        pass