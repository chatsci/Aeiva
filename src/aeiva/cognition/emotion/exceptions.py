# File: cognition/exceptions.py

class ConfigurationError(Exception):
    """Exception raised for errors in the configuration."""
    pass

class UpdateError(Exception):
    """Exception raised for errors during emotion state updates."""
    pass

class RegulationError(Exception):
    """Exception raised for errors during emotion regulation."""
    pass