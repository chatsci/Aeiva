"""
Capability: Declarative resource requirements for tools.

Tools declare what capabilities they need. Safety enforcement
is handled separately by the safety layer (not coupled here).

Usage:
    @tool(capabilities=[Capability.SHELL, Capability.FILESYSTEM])
    async def my_tool(...):
        ...
"""

from enum import Enum, auto
from typing import Set


class Capability(Enum):
    """
    Resource capabilities that tools may require.

    Tools declare these; the safety layer enforces access.
    """

    # Execution
    SHELL = auto()          # Execute shell commands
    CODE_EXEC = auto()      # Execute code (Python, JS, etc.)

    # I/O
    FILESYSTEM = auto()     # Read/write files
    NETWORK = auto()        # Make HTTP requests
    BROWSER = auto()        # Browser automation (superset of NETWORK)

    # System
    PROCESS = auto()        # Manage processes
    SYSTEM_INFO = auto()    # Read system information
    ENV_VARS = auto()       # Access environment variables

    # External Services
    DATABASE = auto()       # Database access
    EXTERNAL_API = auto()   # Third-party API calls

    # Special
    NONE = auto()           # Pure computation, no external resources


# Capability relationships (for future safety layer)
CAPABILITY_IMPLIES: dict[Capability, Set[Capability]] = {
    Capability.BROWSER: {Capability.NETWORK},
    Capability.SHELL: {Capability.FILESYSTEM, Capability.PROCESS, Capability.ENV_VARS},
}


def expand_capabilities(caps: Set[Capability]) -> Set[Capability]:
    """Expand capabilities to include implied ones."""
    expanded = set(caps)
    for cap in caps:
        if cap in CAPABILITY_IMPLIES:
            expanded |= CAPABILITY_IMPLIES[cap]
    return expanded
