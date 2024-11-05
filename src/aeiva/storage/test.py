# test.py

import logging
import uuid

from database_factory import DatabaseConfigFactory, DatabaseFactory

# Set up logging
logging.basicConfig(level=logging.INFO)


def test_milvus():
    """
    Test the DatabaseFactory and DatabaseConfigFactory with Milvus database.
    """
    print("\n--- Testing Milvus Database ---")
    # Create configuration for Milvus
    milvus_config = DatabaseConfigFactory.create(
        'milvus',
        # uri='tcp://localhost:19530',
        uri='storage/milvus_demo.db',
        collection_name='test_collection',
        embedding_model_dims=128,
        metric_type='COSINE',
    )

    # Create Milvus database instance
    milvus_db = DatabaseFactory.create('milvus', milvus_config)

    try:
        # Prepare sample data
        vector_dimension = milvus_config.embedding_model_dims
        vectors = [
            [float(i) for i in range(vector_dimension)],  # Sample vector 1
            [float(i + 1) for i in range(vector_dimension)],  # Sample vector 2
        ]
        payloads = [
            {'name': 'Vector 1', 'description': 'First test vector.'},
            {'name': 'Vector 2', 'description': 'Second test vector.'},
        ]
        ids = [str(uuid.uuid4()), str(uuid.uuid4())]  # Generate unique IDs

        # Insert vectors into the collection
        milvus_db.insert_vectors(
            collection_name=milvus_config.collection_name,
            vectors=vectors,
            payloads=payloads,
            ids=ids
        )
        logging.info(f"Inserted vectors with IDs: {ids}")

        # Search for similar vectors
        query_vector = [float(i + 0.5) for i in range(vector_dimension)]  # Query vector
        search_results = milvus_db.search_vectors(
            collection_name=milvus_config.collection_name,
            query_vector=query_vector,
            top_k=2
        )
        print(f"Milvus Search results:\n{search_results}")

    except Exception as e:
        logging.error(f"An error occurred while testing Milvus: {e}")
    finally:
        # Close the connection
        del milvus_db


def test_neo4j():
    """
    Test the DatabaseFactory and DatabaseConfigFactory with Neo4j database.
    """
    print("\n--- Testing Neo4j Database ---")
    # Create configuration for Neo4j
    neo4j_config = DatabaseConfigFactory.create(
        'neo4j',
        uri='bolt://localhost:7687',
        user='neo4j',
        password='cf57bwP9pcdcEK3',  # Replace with your actual password
        database='neo4j',
        encrypted=False,
    )

    # Create Neo4j database instance
    neo4j_db = DatabaseFactory.create('neo4j', neo4j_config)

    try:
        # Add a node
        node_id = 'node1'
        neo4j_db.add_node(
            node_id=node_id,
            properties={'name': 'Alice', 'age': 30},
            labels=['Person']
        )
        logging.info(f"Added node with ID: {node_id}")

        # Retrieve the node
        node_data = neo4j_db.get_node(node_id)
        print(f"Neo4j Node data: {node_data}")

        # Add another node and create a relationship
        node_id2 = 'node2'
        neo4j_db.add_node(
            node_id=node_id2,
            properties={'name': 'Bob', 'age': 25},
            labels=['Person']
        )
        neo4j_db.add_edge(
            source_id=node_id,
            target_id=node_id2,
            relationship='KNOWS',
            properties={'since': 2020}
        )
        logging.info(f"Added edge between {node_id} and {node_id2}")

        # Get neighbors
        neighbors = neo4j_db.get_neighbors(node_id, relationship='KNOWS', direction='out')
        print(f"Neo4j Neighbors of {node_id}: {neighbors}")

    except Exception as e:
        logging.error(f"An error occurred while testing Neo4j: {e}")
    finally:
        # Close the connection
        neo4j_db.close()


def test_sqlite():
    """
    Test the DatabaseFactory and DatabaseConfigFactory with SQLite database.
    """
    print("\n--- Testing SQLite Database ---")
    # Create configuration for SQLite
    sqlite_config = DatabaseConfigFactory.create(
        'sqlite',
        database='storage/test_database.db'  # Use a file-based database for persistence
    )

    # Create SQLite database instance
    sqlite_db = DatabaseFactory.create('sqlite', sqlite_config)

    try:
        # Create a sample table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            email TEXT UNIQUE
        );
        """
        sqlite_db.execute_sql(create_table_sql)
        logging.info("Created table 'users' in SQLite database.")

        # Insert a record
        record = {'name': 'Alice', 'age': 30, 'email': 'alice@example.com'}
        user_id = sqlite_db.insert_record('users', record)
        logging.info(f"Inserted user with ID: {user_id}")

        # Retrieve the record
        retrieved_record = sqlite_db.get_record('users', user_id)
        print(f"SQLite Retrieved record: {retrieved_record}")

        # Update the record
        updates = {'age': 31}
        sqlite_db.update_record('users', user_id, updates)
        logging.info(f"Updated user with ID: {user_id}")

        # Query records
        conditions = {'age': 31}
        users = sqlite_db.query_records('users', conditions)
        print(f"SQLite Users with age 31: {users}")

    except Exception as e:
        logging.error(f"An error occurred while testing SQLite: {e}")
    finally:
        # Close the database connection
        sqlite_db.close()


def main():
    """
    Main function to run tests for Milvus, Neo4j, and SQLite databases.
    """
    test_milvus()
    test_neo4j()
    test_sqlite()


if __name__ == '__main__':
    main()