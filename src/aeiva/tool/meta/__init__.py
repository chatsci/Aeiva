"""
Meta Tools (Tier 1): Universal primitives.

These tools can do ANYTHING at their respective level:
- shell: Execute ANY command
- filesystem: ANY file operation
- browser: ANY web interaction
"""

from .shell import shell
from .filesystem import filesystem
from .browser import browser

__all__ = [
    "shell",
    "filesystem",
    "browser",
]
