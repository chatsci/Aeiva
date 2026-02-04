"""
Calculator Tool: Safe mathematical expression evaluation.
"""

import ast
import operator
from typing import Dict, Any, Union

from ..decorator import tool
from ..capability import Capability


# Safe operators for evaluation
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> Union[int, float]:
    """Safely evaluate an AST node."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Invalid constant: {node.value}")

    if isinstance(node, ast.BinOp):
        op_func = _OPERATORS.get(type(node.op))
        if not op_func:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return op_func(left, right)

    if isinstance(node, ast.UnaryOp):
        op_func = _OPERATORS.get(type(node.op))
        if not op_func:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op_func(_safe_eval(node.operand))

    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)

    raise ValueError(f"Unsupported expression type: {type(node).__name__}")


@tool(
    description="Evaluate a mathematical expression safely",
    capabilities=[Capability.NONE],
)
async def calculator(
    expression: str,
) -> Dict[str, Any]:
    """
    Safely evaluate a mathematical expression.

    Supports: +, -, *, /, //, %, ** (power)
    Does NOT support: function calls, variable access, imports

    Args:
        expression: Mathematical expression to evaluate.

    Returns:
        Dictionary with result or error.
    """
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree)
        return {"result": result, "error": None}
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError) as e:
        return {"result": None, "error": str(e)}
