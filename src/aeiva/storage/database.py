from abc import ABC, abstractmethod


class Database(ABC):
    """Common base for all database backends."""

    @abstractmethod
    def close(self) -> None:
        """Release resources."""
        ...

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
