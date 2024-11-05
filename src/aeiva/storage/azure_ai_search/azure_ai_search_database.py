import json
import logging
from typing import List, Dict, Any, Optional
from aeiva.storage.vector_database import VectorDatabase  # Replace with your actual import

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.core.exceptions import ResourceNotFoundError
    from azure.search.documents import SearchClient
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        HnswAlgorithmConfiguration,
        ScalarQuantizationCompression,
        SearchField,
        SearchFieldDataType,
        SearchIndex,
        SimpleField,
        VectorSearch,
        VectorSearchProfile,
    )
    from azure.search.documents.models import VectorizedQuery
except ImportError:
    raise ImportError(
        "The 'azure-search-documents' library is required. Please install it using 'pip install azure-search-documents==11.5.1'."
    )

logger = logging.getLogger(__name__)


class AzureAISearchDatabase(VectorDatabase):
    """
    Concrete implementation of VectorStoreBase using Azure Cognitive Search.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the Azure Cognitive Search vector store.

        Args:
            config (Dict[str, Any]): Configuration dictionary.
        """
        self.config = config
        self.index_name = config.get('collection_name')
        self.service_name = config.get('service_name')
        self.api_key = config.get('api_key')
        self.embedding_model_dims = config.get('embedding_model_dims')
        self.use_compression = config.get('use_compression', False)

        if not all([self.service_name, self.api_key, self.index_name, self.embedding_model_dims]):
            raise ValueError("Required configuration parameters are missing.")

        self.create_client(
            uri=None,
            service_name=self.service_name,
            api_key=self.api_key
        )
        self.create_collection(
            collection_name=self.index_name,
            vector_size=self.embedding_model_dims,
            distance_metric='cosine'
        )

    def create_client(
        self,
        uri: Optional[str] = None,
        service_name: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Initializes the client connection to the vector store.

        Args:
            uri (Optional[str]): Not used for Azure Cognitive Search.
            service_name (str): Azure Cognitive Search service name.
            api_key (str): API key for the Azure Cognitive Search service.
            **kwargs: Additional parameters.
        """
        if not service_name or not api_key:
            raise ValueError("Both 'service_name' and 'api_key' must be provided.")

        endpoint = f"https://{service_name}.search.windows.net"
        credential = AzureKeyCredential(api_key)
        self.search_client = SearchClient(
            endpoint=endpoint,
            index_name=self.index_name,
            credential=credential
        )
        self.index_client = SearchIndexClient(
            endpoint=endpoint,
            credential=credential
        )

    def create_collection(self, collection_name: str, vector_size: int, distance_metric: str) -> None:
        """
        Create a new vector collection (index) in Azure Cognitive Search.

        Args:
            collection_name (str): The name of the collection.
            vector_size (int): The dimensionality of the vectors.
            distance_metric (str): The distance metric to use (e.g., 'cosine').
        """
        # Check if the index already exists
        try:
            self.index_client.get_index(collection_name)
            logger.info(f"Index {collection_name} already exists. Skipping creation.")
            return
        except ResourceNotFoundError:
            pass  # Index does not exist, proceed to create

        if self.use_compression:
            vector_type = "Collection(Edm.Half)"
            compression_name = "myCompression"
            compression_configurations = [ScalarQuantizationCompression(compression_name=compression_name)]
        else:
            vector_type = "Collection(Edm.Single)"
            compression_name = None
            compression_configurations = []

        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchField(
                name="vector",
                type=vector_type,
                searchable=True,
                vector_search_dimensions=vector_size,
                vector_search_profile_name="my-vector-config",
            ),
            SimpleField(name="payload", type=SearchFieldDataType.String, searchable=True),
        ]

        vector_search = VectorSearch(
            profiles=[
                VectorSearchProfile(name="my-vector-config", algorithm_configuration_name="my-algorithms-config")
            ],
            algorithms=[HnswAlgorithmConfiguration(name="my-algorithms-config")],
            compressions=compression_configurations,
        )
        index = SearchIndex(name=collection_name, fields=fields, vector_search=vector_search)
        self.index_client.create_or_update_index(index)
        logger.info(f"Index {collection_name} created successfully.")

    def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """
        Insert vectors into the index.

        Args:
            collection_name (str): The name of the collection.
            vectors (List[List[float]]): A list of vectors to insert.
            payloads (Optional[List[Dict[str, Any]]]): Optional metadata associated with each vector.
            ids (Optional[List[str]]): Optional unique identifiers for each vector.
        """
        if collection_name != self.index_name:
            raise ValueError("Collection name does not match initialized index name.")

        if ids is None:
            ids = [str(i) for i in range(len(vectors))]
        if payloads is None:
            payloads = [{} for _ in range(len(vectors))]
        if not (len(ids) == len(vectors) == len(payloads)):
            raise ValueError("Lengths of ids, vectors, and payloads must be equal.")

        documents = [
            {"id": id_, "vector": vector, "payload": json.dumps(payload)}
            for id_, vector, payload in zip(ids, vectors, payloads)
        ]
        self.search_client.upload_documents(documents)
        logger.info(f"Inserted {len(vectors)} vectors into index {collection_name}.")

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
        if collection_name != self.index_name:
            raise ValueError("Collection name does not match initialized index name.")

        vector_query = VectorizedQuery(vector=query_vector, k_nearest_neighbors=top_k, fields="vector")
        search_results = self.search_client.search(vector_queries=[vector_query], top=top_k)

        results = []
        for result in search_results:
            payload = json.loads(result["payload"])
            if filters:
                for key, value in filters.items():
                    if key not in payload or payload[key] != value:
                        continue
            result_dict = {
                "id": result["id"],
                "score": result["@search.score"],
                "payload": payload
            }
            results.append(result_dict)
        return results

    def delete_vector(self, collection_name: str, vector_id: str) -> None:
        """
        Delete a vector from a collection by its ID.

        Args:
            collection_name (str): The name of the collection.
            vector_id (str): The unique identifier of the vector to delete.
        """
        if collection_name != self.index_name:
            raise ValueError("Collection name does not match initialized index name.")
        self.search_client.delete_documents(documents=[{"id": vector_id}])
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
        if collection_name != self.index_name:
            raise ValueError("Collection name does not match initialized index name.")

        document = {"id": vector_id}
        if vector is not None:
            document["vector"] = vector
        if payload is not None:
            document["payload"] = json.dumps(payload)
        self.search_client.merge_or_upload_documents(documents=[document])
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
        if collection_name != self.index_name:
            raise ValueError("Collection name does not match initialized index name.")
        try:
            result = self.search_client.get_document(key=vector_id)
            payload = json.loads(result["payload"])
            vector_data = {
                "id": result["id"],
                "vector": result["vector"],
                "payload": payload
            }
            return vector_data
        except ResourceNotFoundError:
            raise KeyError(f"Vector with ID {vector_id} not found in collection {collection_name}.")

    def list_collections(self) -> List[str]:
        """
        List all available vector collections.

        Returns:
            List[str]: A list of collection names.
        """
        indexes = self.index_client.list_indexes()
        return [index.name for index in indexes]

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete an entire vector collection.

        Args:
            collection_name (str): The name of the collection to delete.
        """
        self.index_client.delete_index(collection_name)
        logger.info(f"Deleted collection {collection_name}.")

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get information about a collection.

        Args:
            collection_name (str): The name of the collection.

        Returns:
            Dict[str, Any]: Information about the collection.
        """
        index = self.index_client.get_index(collection_name)
        return {
            "name": index.name,
            "fields": [field.name for field in index.fields],
            "vector_search": index.vector_search
        }

    def __del__(self):
        """Clean up resources."""
        self.search_client.close()
        self.index_client.close()