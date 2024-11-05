# test_sqlite.py

import logging
from aeiva.storage.sqlite.sqlite_database import SQLiteDatabase
from aeiva.storage.sqlite.sqlite_config import SQLiteConfig


# Custom Exceptions (if not already defined)
class RecordNotFoundError(Exception):
    """Exception raised when a record is not found in the database."""
    pass


def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Configuration for SQLite
    config = SQLiteConfig(database='test_database.db')
    config_dict = {
        'database': config.database
    }

    # Initialize SQLite database
    sqlite_store = SQLiteDatabase(config=config_dict)

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
        sqlite_store.execute_sql(create_table_sql)

        # Insert a record
        record = {'name': 'Alice', 'age': 30, 'email': 'alice@example.com'}
        user_id = sqlite_store.insert_record('users', record)
        logging.info(f"Inserted user with ID: {user_id}")

        # Retrieve the record
        retrieved_record = sqlite_store.get_record('users', user_id)
        print(f"Retrieved record: {retrieved_record}")

        # Update the record
        updates = {'age': 31}
        sqlite_store.update_record('users', user_id, updates)
        logging.info(f"Updated user with ID: {user_id}")

        # Query records
        conditions = {'age': 31}
        users = sqlite_store.query_records('users', conditions)
        print(f"Users with age 31: {users}")

        # Delete the record
        sqlite_store.delete_record('users', user_id)
        logging.info(f"Deleted user with ID: {user_id}")

        # Attempt to retrieve the deleted record
        try:
            sqlite_store.get_record('users', user_id)
        except RecordNotFoundError:
            logging.info(f"Record with ID {user_id} has been deleted and cannot be retrieved.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        # Close the database connection
        sqlite_store.close()


if __name__ == '__main__':
    main()