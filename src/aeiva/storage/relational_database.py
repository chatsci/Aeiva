from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class RelationalDatabase(ABC):
    """
    Abstract base class for relational database operations.
    """

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def query_records(self, table: str, conditions: Optional[Dict[str, Any]] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def begin_transaction(self) -> None:
        """
        Begins a transaction.
        """
        pass

    @abstractmethod
    def commit_transaction(self) -> None:
        """
        Commits the current transaction.
        """
        pass

    @abstractmethod
    def rollback_transaction(self) -> None:
        """
        Rolls back the current transaction.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Closes the database connection and releases resources.
        """
        pass