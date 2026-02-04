"""
Core Tools (Tier 2): Frequently used shortcuts.

These could be done with meta tools, but are used so often
they deserve dedicated tools to save time/tokens:
- web_search: Search the web
- calculator: Safe math evaluation
"""

from .web_search import web_search
from .calculator import calculator

__all__ = [
    "web_search",
    "calculator",
]
