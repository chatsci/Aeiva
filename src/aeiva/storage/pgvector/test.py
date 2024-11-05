# test_pgvector.py

import logging
import uuid
from aeiva.storage.pgvector.pgvector_database import PGVectorDatabase

# Set up logging
logging.basicConfig(level=logging.INFO)

def main():
    # Configuration for PGVector
    pgvector_config = {
        'dbname': 'your_db_name',        # Replace with your database name
        'user': 'your_username',         # Replace with your database username
        'password': 'your_password',     # Replace with your database password
        'host': 'localhost',             # Replace with your database host
        'port': 5432,                    # Replace with your database port
        'collection_name': 'my_table',
        'embedding_model_dims': 128,     # Adjust according to your vector dimensions
        'use_diskann': False,            # Set to True if using DiskANN
    }

    # Initialize PGVector vector store
    pgvector_store = PGVectorDatabase(config=pgvector_config)

    try:
        # Prepare sample data
        vector_dimension = pgvector_config['embedding_model_dims']
        vectors = [
            [float(i) for i in range(vector_dimension)],  # Sample vector 1
            [float(i + 1) for i in range(vector_dimension)],  # Sample vector 2
        ]
        payloads = [
            {'name': 'Vector 1', 'description': 'First test vector.'},
            {'name': 'Vector 2', 'description': 'Second test vector.'},
        ]
        ids = [str(uuid.uuid4()), str(uuid.uuid4())]  # Generate unique IDs

        # Insert vectors into the table
        pgvector_store.insert_vectors(
            collection_name=pgvector_config['collection_name'],
            vectors=vectors,
            payloads=payloads,
            ids=ids
        )
        logging.info(f"Inserted vectors with IDs: {ids}")

        # Search for similar vectors
        query_vector = [float(i + 0.5) for i in range(vector_dimension)]  # Query vector
        search_results = pgvector_store.search_vectors(
            collection_name=pgvector_config['collection_name'],
            query_vector=query_vector,
            top_k=2
        )
        print(f"Search results:\n{search_results}")

        # Retrieve a specific vector
        vector_id = ids[0]
        retrieved_vector = pgvector_store.get_vector(
            collection_name=pgvector_config['collection_name'],
            vector_id=vector_id
        )
        print(f"Retrieved vector:\n{retrieved_vector}")

        # Update a vector's payload
        new_payload = {'name': 'Vector 1 Updated', 'description': 'Updated description.'}
        pgvector_store.update_vector(
            collection_name=pgvector_config['collection_name'],
            vector_id=vector_id,
            payload=new_payload
        )
        logging.info(f"Updated vector with ID: {vector_id}")

        # Retrieve the updated vector
        updated_vector = pgvector_store.get_vector(
            collection_name=pgvector_config['collection_name'],
            vector_id=vector_id
        )
        print(f"Updated vector:\n{updated_vector}")

        # Delete a vector
        pgvector_store.delete_vector(
            collection_name=pgvector_config['collection_name'],
            vector_id=vector_id
        )
        logging.info(f"Deleted vector with ID: {vector_id}")

        # Attempt to retrieve the deleted vector
        try:
            deleted_vector = pgvector_store.get_vector(
                collection_name=pgvector_config['collection_name'],
                vector_id=vector_id
            )
            print(f"Deleted vector:\n{deleted_vector}")
        except KeyError as e:
            logging.info(f"Vector with ID {vector_id} has been deleted and cannot be retrieved.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        # Close the connection
        del pgvector_store

if __name__ == '__main__':
    main()