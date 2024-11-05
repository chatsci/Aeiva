# test_neo4j.py

# NOTE: start neo4j in terminal by: 
# > $NEO4J_HOME/bin/neo4j console

import logging
from aeiva.storage.neo4jdb.neo4j_database import Neo4jDatabase
from aeiva.storage.neo4jdb.neo4j_config import Neo4jConfig

# Set up logging
logging.basicConfig(level=logging.INFO)

def main():
    # Example configuration
    config = Neo4jConfig(
        uri='bolt://localhost:7687',
        user='neo4j',
        password='cf57bwP9pcdcEK3',  # Replace with your actual password
        database='neo4j',
        encrypted=False,
    )

    # Convert the config dataclass to a dictionary
    config_dict = config.to_dict()

    # Initialize Neo4j graph store
    neo4j_store = Neo4jDatabase(config=config_dict)

    try:
        # Add a node
        neo4j_store.add_node(
            node_id='node1',
            properties={'name': 'Alice', 'age': 30},
            labels=['Person']
        )

        # Add another node
        neo4j_store.add_node(
            node_id='node2',
            properties={'name': 'Bob', 'age': 25},
            labels=['Person']
        )

        # Add an edge between nodes
        neo4j_store.add_edge(
            source_id='node1',
            target_id='node2',
            relationship='KNOWS',
            properties={'since': 2020}
        )

        # Get a node
        node_data = neo4j_store.get_node('node1')
        print(f"Node1 data: {node_data}")

        # Get neighbors
        neighbors = neo4j_store.get_neighbors('node1', relationship='KNOWS', direction='out')
        print(f"Neighbors of node1: {neighbors}")

        # Update a node
        neo4j_store.update_node('node1', properties={'age': 31})

        # Query nodes
        nodes = neo4j_store.query_nodes(properties={'age': 31}, labels=['Person'])
        print(f"Nodes with age 31: {nodes}")

        # Execute a custom query
        result = neo4j_store.execute_query("MATCH (n:Person) RETURN n.name AS name")
        print(f"Custom query result: {result}")

        # Delete a node
        neo4j_store.delete_node('node2')

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        # Close the connection
        neo4j_store.close()

if __name__ == '__main__':
    main()