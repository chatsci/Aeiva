# sqlite_db.py

import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from aeiva.storage.relational_database import RelationalDatabase

# Custom Exceptions
class RecordNotFoundError(Exception):
    """Exception raised when a record is not found in the database."""
    pass


class StorageError(Exception):
    """Exception raised when there is a storage-related error in the database."""
    pass


class SQLiteDatabase(RelationalDatabase):
    """
    Concrete implementation of RelationalStoreBase using SQLite.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the SQLite database connection.

        Args:
            config (Dict[str, Any]): Configuration dictionary.
        """
        self.config = config
        self.database = config.get('database', ':memory:')
        self.connection = None
        self.cursor = None
        self.connect()

    def connect(self) -> None:
        """
        Establishes a connection to the SQLite database.
        """
        try:
            self.connection = sqlite3.connect(self.database)
            self.connection.row_factory = sqlite3.Row  # To get dict-like rows
            self.cursor = self.connection.cursor()
            # self.connection.execute('PRAGMA foreign_keys = ON')  # Enable foreign key support
        except sqlite3.Error as e:
            raise ConnectionError(f"Failed to connect to SQLite database: {e}")

    def close(self) -> None:
        """
        Closes the database connection and releases resources.
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    def insert_record(self, table: str, record: Dict[str, Any]) -> Any:
        """
        Inserts a record into a table.

        Args:
            table (str): The name of the table.
            record (Dict[str, Any]): A dictionary representing the record to insert.

        Returns:
            Any: The primary key of the inserted record.

        Raises:
            StorageError: If there is an issue inserting the record.
        """
        try:
            columns = ', '.join(record.keys())
            placeholders = ', '.join('?' for _ in record)
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            values = list(record.values())
            self.cursor.execute(sql, values)
            self.connection.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError as e:
            self.connection.rollback()
            raise StorageError(f"Integrity error: {e}")
        except sqlite3.Error as e:
            self.connection.rollback()
            raise StorageError(f"Failed to insert record: {e}")

    def get_record(self, table: str, primary_key: Any) -> Dict[str, Any]:
        """
        Retrieves a record by its primary key.

        Args:
            table (str): The name of the table.
            primary_key (Any): The primary key of the record.

        Returns:
            Dict[str, Any]: The retrieved record.

        Raises:
            RecordNotFoundError: If the record does not exist.
            StorageError: If there is an issue retrieving the record.
        """
        try:
            sql = f"SELECT * FROM {table} WHERE id = ?"
            self.cursor.execute(sql, (primary_key,))
            row = self.cursor.fetchone()
            if row is None:
                raise RecordNotFoundError(f"Record with primary key {primary_key} not found in table '{table}'.")
            return dict(row)
        except sqlite3.Error as e:
            raise StorageError(f"Failed to get record: {e}")

    def update_record(self, table: str, primary_key: Any, updates: Dict[str, Any]) -> None:
        """
        Updates a record in a table.

        Args:
            table (str): The name of the table.
            primary_key (Any): The primary key of the record.
            updates (Dict[str, Any]): A dictionary of fields to update.

        Raises:
            RecordNotFoundError: If the record does not exist.
            StorageError: If there is an issue updating the record.
        """
        try:
            set_clause = ', '.join(f"{key} = ?" for key in updates.keys())
            sql = f"UPDATE {table} SET {set_clause} WHERE id = ?"
            values = list(updates.values()) + [primary_key]
            self.cursor.execute(sql, values)
            if self.cursor.rowcount == 0:
                self.connection.rollback()
                raise RecordNotFoundError(f"Record with primary key {primary_key} not found in table '{table}'.")
            self.connection.commit()
        except sqlite3.Error as e:
            self.connection.rollback()
            raise StorageError(f"Failed to update record: {e}")

    def delete_record(self, table: str, primary_key: Any) -> None:
        """
        Deletes a record from a table.

        Args:
            table (str): The name of the table.
            primary_key (Any): The primary key of the record.

        Raises:
            RecordNotFoundError: If the record does not exist.
            StorageError: If there is an issue deleting the record.
        """
        try:
            sql = f"DELETE FROM {table} WHERE id = ?"
            self.cursor.execute(sql, (primary_key,))
            if self.cursor.rowcount == 0:
                self.connection.rollback()
                raise RecordNotFoundError(f"Record with primary key {primary_key} not found in table '{table}'.")
            self.connection.commit()
        except sqlite3.Error as e:
            self.connection.rollback()
            raise StorageError(f"Failed to delete record: {e}")

    def query_records(
        self,
        table: str,
        conditions: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Queries records from a table based on conditions.

        Args:
            table (str): The name of the table.
            conditions (Optional[Dict[str, Any]]): Conditions to filter records.
            limit (Optional[int]): Maximum number of records to return.
            offset (Optional[int]): Number of records to skip.

        Returns:
            List[Dict[str, Any]]: A list of records matching the query.

        Raises:
            StorageError: If there is an issue querying records.
        """
        try:
            sql = f"SELECT * FROM {table}"
            params = []
            if conditions:
                where_clause = ' AND '.join(f"{key} = ?" for key in conditions.keys())
                sql += f" WHERE {where_clause}"
                params.extend(conditions.values())
            if limit is not None:
                sql += f" LIMIT {limit}"
            if offset is not None:
                sql += f" OFFSET {offset}"
            self.cursor.execute(sql, params)
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            raise StorageError(f"Failed to query records: {e}")

    def execute_sql(self, query: str, params: Optional[Tuple] = None):
        """
        Executes a SQL query and returns the cursor.
        
        Args:
            query (str): The SQL query to execute.
            params (Optional[Tuple]): Parameters to substitute into the query.
        
        Returns:
            sqlite3.Cursor: The cursor after executing the query.
        """
        cursor = self.connection.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            # For SELECT queries, do not commit. For INSERT/UPDATE/DELETE, you may need to commit.
            if query.strip().upper().startswith("SELECT"):
                return cursor
            else:
                self.connection.commit()
                return cursor
        except sqlite3.Error as e:
            print(f"SQLite query failed: {e}")
            raise e

    def begin_transaction(self) -> None:
        """
        Begins a transaction.
        """
        self.connection.isolation_level = None
        self.cursor.execute('BEGIN')

    def commit_transaction(self) -> None:
        """
        Commits the current transaction.
        """
        self.connection.commit()
        self.connection.isolation_level = None

    def rollback_transaction(self) -> None:
        """
        Rolls back the current transaction.
        """
        self.connection.rollback()
        self.connection.isolation_level = None