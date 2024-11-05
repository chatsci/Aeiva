import logging
from typing import List, Dict, Any, Optional
from aeiva.storage.vector_database import VectorDatabase

try:
    import psycopg2
    from psycopg2.extras import execute_values, Json
except ImportError:
    raise ImportError("The 'psycopg2' library is required. Please install it using 'pip install psycopg2'.")

logger = logging.getLogger(__name__)


class PGVectorDatabase(VectorDatabase):
    """
    Concrete implementation of VectorStoreBase using PGVector.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the PGVector vector store.

        Args:
            config (Dict[str, Any]): Configuration dictionary.
        """
        self.config = config
        self.collection_name = config.get('collection_name')
        self.dbname = config.get('dbname')
        self.user = config.get('user')
        self.password = config.get('password')
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 5432)
        self.embedding_model_dims = config.get('embedding_model_dims')
        self.use_diskann = config.get('use_diskann', False)

        if not all([self.collection_name, self.dbname, self.user, self.password, self.embedding_model_dims]):
            raise ValueError("Required configuration parameters are missing.")

        self.create_client()
        self.create_collection(
            collection_name=self.collection_name,
            vector_size=self.embedding_model_dims,
            distance_metric='cosine'  # PGVector uses cosine by default
        )

    def create_client(self, **kwargs) -> None:
        """
        Initializes the client connection to the PGVector database.

        Args:
            **kwargs: Additional parameters.
        """
        try:
            self.conn = psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                **kwargs
            )
            self.cur = self.conn.cursor()
            logger.info("Connected to PGVector database.")
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to PGVector database: {e}")
            raise ConnectionError(f"Failed to connect to PGVector database: {e}")

    def create_collection(self, collection_name: str, vector_size: int, distance_metric: str) -> None:
        """
        Create a new vector collection (table) in PGVector.

        Args:
            collection_name (str): The name of the collection.
            vector_size (int): The dimensionality of the vectors.
            distance_metric (str): The distance metric to use (e.g., 'cosine').
        """
        # Check if table exists
        self.cur.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name=%s);",
            (collection_name,)
        )
        exists = self.cur.fetchone()[0]
        if exists:
            logger.info(f"Table {collection_name} already exists. Skipping creation.")
            return

        # Create table
        create_table_query = f"""
        CREATE TABLE {collection_name} (
            id VARCHAR(64) PRIMARY KEY,
            vector vector({vector_size}),
            payload JSONB
        );
        """
        self.cur.execute(create_table_query)
        self.conn.commit()
        logger.info(f"Table {collection_name} created successfully.")

        # Create index if use_diskann is True
        if self.use_diskann:
            create_index_query = f"""
            CREATE INDEX {collection_name}_vector_idx
            ON {collection_name}
            USING ivfflat (vector vector_cosine_ops)
            WITH (lists = 100);
            """
            self.cur.execute(create_index_query)
            self.conn.commit()
            logger.info(f"Index created on table {collection_name}.")

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
            raise ValueError("PGVector requires IDs to be provided for each vector.")
        if payloads is None:
            payloads = [{} for _ in range(len(vectors))]
        if not (len(ids) == len(vectors) == len(payloads)):
            raise ValueError("Lengths of ids, vectors, and payloads must be equal.")

        records = [
            (id_, vector, Json(payload))
            for id_, vector, payload in zip(ids, vectors, payloads)
        ]
        insert_query = f"INSERT INTO {collection_name} (id, vector, payload) VALUES %s;"
        execute_values(self.cur, insert_query, records)
        self.conn.commit()
        logger.info(f"Inserted {len(vectors)} vectors into table {collection_name}.")

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

        filter_clause = ""
        params = [query_vector]

        if filters:
            filter_conditions = []
            for key, value in filters.items():
                filter_conditions.append(f"payload ->> %s = %s")
                params.extend([key, str(value)])
            filter_clause = "WHERE " + " AND ".join(filter_conditions)

        search_query = f"""
        SELECT id, vector, payload, 1 - (vector <#> %s::vector) AS score
        FROM {collection_name}
        {filter_clause}
        ORDER BY vector <#> %s::vector
        LIMIT %s;
        """
        params.extend([query_vector, top_k])
        self.cur.execute(search_query, params)
        results = self.cur.fetchall()

        output = []
        for row in results:
            result = {
                'id': row[0],
                'score': row[3],
                'payload': row[2]
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

        delete_query = f"DELETE FROM {collection_name} WHERE id = %s;"
        self.cur.execute(delete_query, (vector_id,))
        self.conn.commit()
        logger.info(f"Deleted vector with ID {vector_id} from table {collection_name}.")

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

        if vector is not None:
            update_query = f"UPDATE {collection_name} SET vector = %s WHERE id = %s;"
            self.cur.execute(update_query, (vector, vector_id))
        if payload is not None:
            update_query = f"UPDATE {collection_name} SET payload = %s WHERE id = %s;"
            self.cur.execute(update_query, (Json(payload), vector_id))
        self.conn.commit()
        logger.info(f"Updated vector with ID {vector_id} in table {collection_name}.")

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

        select_query = f"SELECT id, vector, payload FROM {collection_name} WHERE id = %s;"
        self.cur.execute(select_query, (vector_id,))
        result = self.cur.fetchone()

        if not result:
            raise KeyError(f"Vector with ID {vector_id} not found in table {collection_name}.")

        vector_data = {
            'id': result[0],
            'vector': result[1],
            'payload': result[2]
        }
        return vector_data

    def list_collections(self) -> List[str]:
        """
        List all available vector collections (tables).

        Returns:
            List[str]: A list of collection names.
        """
        self.cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
        )
        tables = self.cur.fetchall()
        return [table[0] for table in tables]

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete an entire vector collection.

        Args:
            collection_name (str): The name of the collection to delete.
        """
        drop_query = f"DROP TABLE IF EXISTS {collection_name};"
        self.cur.execute(drop_query)
        self.conn.commit()
        logger.info(f"Deleted table {collection_name}.")

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get information about a collection.

        Args:
            collection_name (str): The name of the collection.

        Returns:
            Dict[str, Any]: Information about the collection.
        """
        self.cur.execute(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s;",
            (collection_name,)
        )
        columns = self.cur.fetchall()
        info = {
            'name': collection_name,
            'columns': {column[0]: column[1] for column in columns}
        }
        return info

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'cur') and self.cur:
            self.cur.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
        logger.info("Closed connection to PGVector database.")