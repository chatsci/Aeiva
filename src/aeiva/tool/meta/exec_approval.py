"""
Exec Approval Tool: Ask the host to approve a sensitive action.

This is a control tool (no side effects by itself). The actual enforcement
must be done on the host/router side.
"""

from typing import Dict, Optional

from ..decorator import tool
from ..capability import Capability


@tool(
    description="Request approval for a potentially destructive or sensitive action.",
    capabilities=[Capability.SHELL],
)
async def exec_approval(
    action: str,
    reason: Optional[str] = None,
    details: Optional[str] = None,
) -> Dict[str, str]:
    """
    Request approval before executing a sensitive action.

    Args:
        action: Short label for the action (e.g., 'delete file', 'install package').
        reason: Why the action is needed.
        details: Additional details for the user.

    Returns:
        Simple acknowledgement payload.
    """
    return {
        "action": action,
        "reason": reason or "",
        "details": details or "",
        "approved": "pending",
    }
