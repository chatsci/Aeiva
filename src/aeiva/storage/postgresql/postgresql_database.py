# postgresql_db.py

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Any, Dict, List, Optional
from aeiva.storage.relational_database import RelationalDatabase

# Custom Exceptions
class RecordNotFoundError(Exception):
    """Exception raised when a record is not found in the database."""
    pass


class StorageError(Exception):
    """Exception raised when there is a storage-related error in the database."""
    pass


class PostgreSQLDatabase(RelationalDatabase):
    """
    Concrete implementation of RelationalStoreBase using PostgreSQL.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the PostgreSQL database connection.

        Args:
            config (Dict[str, Any]): Configuration dictionary.
        """
        self.config = config
        self.connection = None
        self.cursor = None
        self.connect()

    def connect(self) -> None:
        """
        Establishes a connection to the PostgreSQL database.
        """
        try:
            self.connection = psycopg2.connect(
                dbname=self.config.get('dbname'),
                user=self.config.get('user'),
                password=self.config.get('password'),
                host=self.config.get('host'),
                port=self.config.get('port')
            )
            self.connection.autocommit = True  # Enable autocommit for DDL statements
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        except psycopg2.Error as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL database: {e}")

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
            placeholders = ', '.join(f"%({key})s" for key in record.keys())
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING id"
            self.cursor.execute(sql, record)
            result = self.cursor.fetchone()
            return result['id']
        except psycopg2.IntegrityError as e:
            self.connection.rollback()
            raise StorageError(f"Integrity error: {e}")
        except psycopg2.Error as e:
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
            sql = f"SELECT * FROM {table} WHERE id = %s"
            self.cursor.execute(sql, (primary_key,))
            row = self.cursor.fetchone()
            if row is None:
                raise RecordNotFoundError(f"Record with primary key {primary_key} not found in table '{table}'.")
            return dict(row)
        except psycopg2.Error as e:
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
            set_clause = ', '.join(f"{key} = %({key})s" for key in updates.keys())
            sql = f"UPDATE {table} SET {set_clause} WHERE id = %(id)s"
            updates['id'] = primary_key
            self.cursor.execute(sql, updates)
            if self.cursor.rowcount == 0:
                self.connection.rollback()
                raise RecordNotFoundError(f"Record with primary key {primary_key} not found in table '{table}'.")
        except psycopg2.Error as e:
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
            sql = f"DELETE FROM {table} WHERE id = %s"
            self.cursor.execute(sql, (primary_key,))
            if self.cursor.rowcount == 0:
                self.connection.rollback()
                raise RecordNotFoundError(f"Record with primary key {primary_key} not found in table '{table}'.")
        except psycopg2.Error as e:
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
            params = {}
            if conditions:
                where_clause = ' AND '.join(f"{key} = %({key})s" for key in conditions.keys())
                sql += f" WHERE {where_clause}"
                params.update(conditions)
            if limit is not None:
                sql += f" LIMIT {limit}"
            if offset is not None:
                sql += f" OFFSET {offset}"
            self.cursor.execute(sql, params)
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]
        except psycopg2.Error as e:
            raise StorageError(f"Failed to query records: {e}")

    def execute_sql(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """
        Executes a raw SQL query.

        Args:
            query (str): The SQL query string.
            parameters (Optional[Dict[str, Any]]): Parameters for parameterized queries.

        Returns:
            Any: The result of the query.

        Raises:
            StorageError: If there is an issue executing the query.
        """
        cursor = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            if parameters:
                cursor.execute(query, parameters)
            else:
                cursor.execute(query)
            if query.strip().upper().startswith("SELECT"):
                return cursor
            else:
                self.connection.commit()
                return cursor
        except psycopg2.Error as e:
            self.connection.rollback()
            raise StorageError(f"Failed to execute SQL query: {e}")

    def begin_transaction(self) -> None:
        """
        Begins a transaction.
        """
        self.connection.autocommit = False

    def commit_transaction(self) -> None:
        """
        Commits the current transaction.
        """
        self.connection.commit()
        self.connection.autocommit = True

    def rollback_transaction(self) -> None:
        """
        Rolls back the current transaction.
        """
        self.connection.rollback()
        self.connection.autocommit = True