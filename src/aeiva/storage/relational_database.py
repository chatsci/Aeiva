from abc import abstractmethod
from typing import Any, Dict, List, Optional

from aeiva.storage.database import Database


class RelationalDatabase(Database):
    """Abstract base class for relational database operations."""

    @abstractmethod
    def insert_record(self, table: str, record: Dict[str, Any]) -> Any:
        """Insert a record into a table."""
        pass

    @abstractmethod
    def get_record(self, table: str, primary_key: Any) -> Dict[str, Any]:
        """Retrieve a record by its primary key."""
        pass

    @abstractmethod
    def update_record(self, table: str, primary_key: Any, updates: Dict[str, Any]) -> None:
        """Update a record in a table."""
        pass

    @abstractmethod
    def delete_record(self, table: str, primary_key: Any) -> None:
        """Delete a record from a table."""
        pass

    @abstractmethod
    def query_records(self, table: str, conditions: Optional[Dict[str, Any]] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """Query records from a table based on conditions."""
        pass

    @abstractmethod
    def execute_sql(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a raw SQL query."""
        pass

    @abstractmethod
    def begin_transaction(self) -> None:
        """Begin a transaction."""
        pass

    @abstractmethod
    def commit_transaction(self) -> None:
        """Commit the current transaction."""
        pass

    @abstractmethod
    def rollback_transaction(self) -> None:
        """Roll back the current transaction."""
        pass
