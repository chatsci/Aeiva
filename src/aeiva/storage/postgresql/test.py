# test_postgresql.py

import logging
from aeiva.storage.postgresql.postgresql_database import PostgreSQLDatabase  # Replace with your actual import
from aeiva.storage.postgresql.postgresql_config import PostgreSQLConfig  # Replace with your actual import

# Custom Exceptions (if not already defined)
class RecordNotFoundError(Exception):
    """Exception raised when a record is not found in the database."""
    pass


def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Configuration for PostgreSQL
    config = PostgreSQLConfig(
        dbname='your_db_name',       # Replace with your database name
        user='your_username',        # Replace with your username
        password='your_password',    # Replace with your password
        host='localhost',
        port=5432
    )
    config_dict = {
        'dbname': config.dbname,
        'user': config.user,
        'password': config.password,
        'host': config.host,
        'port': config.port
    }

    # Initialize PostgreSQL database
    postgres_store = PostgreSQLDatabase(config=config_dict)

    try:
        # Create a sample table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            email TEXT UNIQUE
        );
        """
        postgres_store.execute_sql(create_table_sql)

        # Insert a record
        record = {'name': 'Alice', 'age': 30, 'email': 'alice@example.com'}
        user_id = postgres_store.insert_record('users', record)
        logging.info(f"Inserted user with ID: {user_id}")

        # Retrieve the record
        retrieved_record = postgres_store.get_record('users', user_id)
        print(f"Retrieved record: {retrieved_record}")

        # Update the record
        updates = {'age': 31}
        postgres_store.update_record('users', user_id, updates)
        logging.info(f"Updated user with ID: {user_id}")

        # Query records
        conditions = {'age': 31}
        users = postgres_store.query_records('users', conditions)
        print(f"Users with age 31: {users}")

        # Delete the record
        postgres_store.delete_record('users', user_id)
        logging.info(f"Deleted user with ID: {user_id}")

        # Attempt to retrieve the deleted record
        try:
            postgres_store.get_record('users', user_id)
        except RecordNotFoundError:
            logging.info(f"Record with ID {user_id} has been deleted and cannot be retrieved.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        # Close the database connection
        postgres_store.close()


if __name__ == '__main__':
    main()