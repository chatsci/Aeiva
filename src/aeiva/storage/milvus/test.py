# test_milvus.py

import logging
import uuid
from aeiva.storage.milvus.milvus_database import MilvusDatabase  # Replace with the actual path if necessary

# Set up logging
logging.basicConfig(level=logging.INFO)

def main():
    # Example configuration for Milvus
    milvus_config = {
        # 'uri': 'tcp://localhost:19530',  # Milvus server URI
        'uri': 'storage/milvus_demo.db',
        'collection_name': 'my_collection',
        'embedding_model_dims': 128,  # Adjust the dimension according to your embeddings
        'metric_type': 'COSINE',  # 'L2', 'IP', or 'COSINE'
        'user': None,  # If authentication is enabled, provide the username
        'password': None,  # If authentication is enabled, provide the password
        'token': None,  # If using a token for authentication
    }

    # Initialize Milvus vector store
    milvus_store = MilvusDatabase(config=milvus_config)

    try:
        # Prepare sample data
        vector_dimension = milvus_config['embedding_model_dims']
        vectors = [
            [float(i) for i in range(vector_dimension)],  # Sample vector 1
            [float(i + 1) for i in range(vector_dimension)],  # Sample vector 2
        ]
        payloads = [
            {'name': 'Vector 1', 'description': 'This is the first test vector.'},
            {'name': 'Vector 2', 'description': 'This is the second test vector.'},
        ]
        ids = [str(uuid.uuid4()), str(uuid.uuid4())]  # Generate unique IDs for the vectors

        # Insert vectors into the collection
        milvus_store.insert_vectors(
            collection_name=milvus_config['collection_name'],
            vectors=vectors,
            payloads=payloads,
            ids=ids
        )
        logging.info(f"Inserted vectors with IDs: {ids}")

        # Search for similar vectors
        query_vector = [float(i + 0.5) for i in range(vector_dimension)]  # Query vector
        search_results = milvus_store.search_vectors(
            collection_name=milvus_config['collection_name'],
            query_vector=query_vector,
            top_k=2
        )
        print(f"Search results:\n{search_results}")

        # Retrieve a specific vector
        vector_id = ids[0]
        retrieved_vector = milvus_store.get_vector(
            collection_name=milvus_config['collection_name'],
            vector_id=vector_id
        )
        print(f"Retrieved vector:\n{retrieved_vector}")

        # Update a vector's payload
        new_payload = {'name': 'Vector 1 Updated', 'description': 'Updated description.'}
        milvus_store.update_vector(
            collection_name=milvus_config['collection_name'],
            vector_id=vector_id,
            payload=new_payload
        )
        logging.info(f"Updated vector with ID: {vector_id}")

        # Retrieve the updated vector
        updated_vector = milvus_store.get_vector(
            collection_name=milvus_config['collection_name'],
            vector_id=vector_id
        )
        print(f"Updated vector:\n{updated_vector}")

        # Delete a vector
        milvus_store.delete_vector(
            collection_name=milvus_config['collection_name'],
            vector_id=vector_id
        )
        logging.info(f"Deleted vector with ID: {vector_id}")

        # Attempt to retrieve the deleted vector
        try:
            deleted_vector = milvus_store.get_vector(
                collection_name=milvus_config['collection_name'],
                vector_id=vector_id
            )
            print(f"Deleted vector:\n{deleted_vector}")
        except KeyError as e:
            logging.info(f"Vector with ID {vector_id} has been deleted and cannot be retrieved.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        # Close the connection
        del milvus_store

if __name__ == '__main__':
    main()