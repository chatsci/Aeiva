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
    """Concrete implementation of VectorDatabase using embedded ChromaDB."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.collection_name = config.get('collection_name')
        self.path = config.get('path', 'storage/chromadb')

        if not self.collection_name:
            raise ValueError("Collection name must be provided in the configuration.")

        settings = Settings(
            anonymized_telemetry=False,
            persist_directory=self.path,
            is_persistent=True,
        )
        self.client = chromadb.Client(settings)
        logger.info("ChromaDB client initialized (embedded, path=%s).", self.path)

        self.collection = self.client.get_or_create_collection(name=self.collection_name)
        logger.info("Collection '%s' ready.", self.collection_name)

    def close(self) -> None:
        self.collection = None
        self.client = None

    def create_collection(self, collection_name: str, vector_size: int, distance_metric: str) -> None:
        self.collection = self.client.get_or_create_collection(name=collection_name)
        self.collection_name = collection_name
        logger.info("Collection '%s' ready.", collection_name)

    def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        if collection_name != self.collection_name:
            raise ValueError("Collection name does not match initialized collection name.")

        if ids is None:
            ids = [str(i) for i in range(len(vectors))]
        if payloads is not None:
            if not (len(ids) == len(vectors) == len(payloads)):
                raise ValueError("Lengths of ids, vectors, and payloads must be equal.")
        elif len(ids) != len(vectors):
            raise ValueError("Lengths of ids and vectors must be equal.")

        self.collection.add(ids=ids, embeddings=vectors, metadatas=payloads)
        logger.info("Inserted %d vectors into collection %s.", len(vectors), collection_name)

    def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        if collection_name != self.collection_name:
            raise ValueError("Collection name does not match initialized collection name.")

        results = self.collection.query(
            query_embeddings=[query_vector],
            where=filters,
            n_results=top_k
        )
        output = []
        for ids, distances, metadatas in zip(results['ids'], results['distances'], results['metadatas']):
            for i in range(len(ids)):
                output.append({
                    'id': ids[i],
                    'score': distances[i],
                    'payload': metadatas[i],
                })
        return output

    def delete_vector(self, collection_name: str, vector_id: str) -> None:
        if collection_name != self.collection_name:
            raise ValueError("Collection name does not match initialized collection name.")

        self.collection.delete(ids=[vector_id])
        logger.info("Deleted vector with ID %s from collection %s.", vector_id, collection_name)

    def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: Optional[List[float]] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> None:
        if collection_name != self.collection_name:
            raise ValueError("Collection name does not match initialized collection name.")

        self.collection.update(
            ids=[vector_id],
            embeddings=[vector] if vector else None,
            metadatas=[payload] if payload else None,
        )
        logger.info("Updated vector with ID %s in collection %s.", vector_id, collection_name)

    def get_vector(self, collection_name: str, vector_id: str) -> Dict[str, Any]:
        if collection_name != self.collection_name:
            raise ValueError("Collection name does not match initialized collection name.")

        result = self.collection.get(ids=[vector_id], include=["embeddings", "metadatas"])
        if not result['ids']:
            raise KeyError(f"Vector with ID {vector_id} not found in collection {collection_name}.")

        return {
            'id': result['ids'][0],
            'vector': result['embeddings'][0] if 'embeddings' in result else None,
            'payload': result['metadatas'][0],
        }

    def list_collections(self) -> List[str]:
        collections = self.client.list_collections()
        return [collection.name for collection in collections]

    def delete_collection(self, collection_name: str) -> None:
        self.client.delete_collection(name=collection_name)
        logger.info("Deleted collection %s.", collection_name)

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        collection = self.client.get_collection(name=collection_name)
        return {
            'name': collection.name,
            'metadata': collection.metadata,
        }
