# aeiva/hypergraph/exceptions.py

class HypergraphError(Exception):
    """
    Custom exception class for Hypergraph-related errors.
    """
    def __init__(self, message: str = "An error occurred in the Hypergraph module."):
        super().__init__(message)
