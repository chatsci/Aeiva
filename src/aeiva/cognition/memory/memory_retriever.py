# memory_retriever.py

import logging
from typing import List, Any, Optional

from aeiva.cognition.memory.memory_unit import MemoryUnit
from aeiva.cognition.memory.memory_storage import MemoryStorage
from aeiva.embedding.embedder import Embedder  # Assuming you have an Embedder class


class MemoryRetrieverError(Exception):
    """Exception raised when an error occurs in the MemoryRetriever."""
    pass


class MemoryRetriever:
    """
    A class to retrieve memory units based on various retrieval algorithms.

    Supported retrieval types:
        - 'similar': Retrieves memory units similar to a given query based on embeddings.
        - 'related': Retrieves memory units related to a specified query based on relationships.
    """

    def __init__(self, embedder: Embedder, storage: MemoryStorage):
        """
        Initializes the MemoryRetriever.

        Args:
            embedder (Embedder): An instance responsible for generating embeddings.
            storage (MemoryStorage): An instance managing data storage and retrieval.
        """
        self.embedder = embedder
        self.storage = storage
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Initialized MemoryRetriever with provided embedder and storage.")

    def retrieve(
        self,
        query: Any,
        retrieve_type: str,
        **kwargs
    ) -> List[MemoryUnit]:
        """
        Factory method to retrieve memory units based on the specified retrieval type.

        Args:
            query (Any): The query for retrieval.
            retrieve_type (str): The type of retrieval ('similar' or 'related').
            **kwargs: Additional parameters required for specific retrieval types.
                For 'similar' retrieval:
                    - top_k (int): The number of similar units to retrieve.
                For 'related' retrieval:
                    - relationship (Optional[str]): The type of relationship to filter by.

        Returns:
            List[MemoryUnit]: A list of retrieved memory units.

        Raises:
            MemoryRetrieverError: If an unknown retrieval_type is provided or if retrieval fails.
        """
        self.logger.info(f"Initiating retrieval of type '{retrieve_type}' with query: {query}")
        try:
            if retrieve_type == 'similar':
                top_k = kwargs.get('top_k', 5)
                self.logger.debug(f"Retrieval Type: 'similar' with top_k={top_k}")
                return self.retrieve_similar(query, top_k)
            elif retrieve_type == 'related':
                relationship = kwargs.get('relationship')
                self.logger.debug(f"Retrieval Type: 'related' with relationship='{relationship}'")
                return self.retrieve_related(query, relationship)
            else:
                self.logger.error(f"Unknown retrieve_type: {retrieve_type}")
                raise MemoryRetrieverError(f"Unknown retrieve_type: {retrieve_type}")
        except MemoryRetrieverError:
            # Re-raise custom errors without modification
            raise
        except Exception as e:
            self.logger.error(f"Failed to retrieve memory units: {e}")
            raise MemoryRetrieverError(f"Failed to retrieve memory units: {e}") from e

    def retrieve_similar(self, query: Any, top_k: int = 5) -> List[MemoryUnit]:
        """
        Retrieves memory units similar to the given input based on embeddings.

        Args:
            query (Any): The query for retrieval.
            top_k (int): The number of similar units to retrieve.

        Returns:
            List[MemoryUnit]: A list of similar memory units.

        Raises:
            MemoryRetrieverError: If retrieval fails due to embedding generation or storage issues.
        """
        self.logger.info(f"Retrieving top {top_k} similar MemoryUnits based on the query.")
        try:
            # Generate embedding for the query
            self.logger.debug("Generating embedding for the query.")
            embedding_response = self.embedder.embed(query)
            if not embedding_response.get("data"):
                self.logger.error("Failed to generate embedding for the query.")
                raise MemoryRetrieverError("Failed to generate embedding for the query.")

            query_embedding = embedding_response["data"][0].get("embedding")
            if not query_embedding:
                self.logger.error("Embedding data is missing in the response.")
                raise MemoryRetrieverError("Embedding data is missing in the response.")

            self.logger.debug(f"Embedding generated successfully: {query_embedding}")

            # Perform similarity search via MemoryStorage
            self.logger.debug("Performing similarity search in the vector database.")
            similar_units = self.storage.retrieve_similar_memory_units(query_embedding, top_k)
            self.logger.info(f"Retrieved {len(similar_units)} similar MemoryUnits.")
            return similar_units

        except MemoryRetrieverError:
            # Re-raise custom errors without modification
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during retrieve_similar: {e}")
            raise MemoryRetrieverError(f"Unexpected error during retrieve_similar: {e}") from e

    def retrieve_related(
        self,
        query: Any,
        relationship: Optional[str] = None
    ) -> List[MemoryUnit]:  # TODO: revise the method later
        """
        Retrieves memory units related to the given query based on relationships.

        Args:
            query (Any): The query for retrieval. Expected to be a MemoryUnit ID or similar identifier.
            relationship (Optional[str]): The type of relationship to filter by.

        Returns:
            List[MemoryUnit]: A list of related memory units.

        Raises:
            MemoryRetrieverError: If retrieval fails due to storage issues or invalid queries.
        """
        self.logger.info(f"Retrieving memories related to the query with relationship: {relationship}")
        try:
            # Assuming 'query' is a MemoryUnit ID or can be used to fetch a MemoryUnit
            self.logger.debug("Fetching the target MemoryUnit from storage.")
            target_memory_unit = self.storage.get_memory_unit(query)
            if not target_memory_unit:
                self.logger.error(f"MemoryUnit with ID '{query}' not found.")
                raise MemoryRetrieverError(f"MemoryUnit with ID '{query}' not found.")

            self.logger.debug(f"MemoryUnit fetched successfully: {target_memory_unit}")

            # Perform related retrieval via MemoryStorage
            self.logger.debug("Retrieving related MemoryUnits from the graph database.")
            related_units = self.storage.retrieve_related_memory_units(target_memory_unit.id, relationship)
            self.logger.info(f"Retrieved {len(related_units)} related MemoryUnits.")
            return related_units

        except MemoryRetrieverError:
            # Re-raise custom errors without modification
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during retrieve_related: {e}")
            raise MemoryRetrieverError(f"Unexpected error during retrieve_related: {e}") from e

    def handle_error(self, error: Exception):
        """
        Handles errors by logging or performing other necessary actions.

        Args:
            error (Exception): The exception to handle.
        """
        # Implement any error handling logic here
        # For now, we'll just log the error
        self.logger.error(f"An error occurred: {error}")