# common/security.py

import os
from pathlib import Path
import logging
from typing import Dict, Type

from aeiva.tool.toolkit.toolkit_config import ToolkitConfig

logger = logging.getLogger(__name__)

def sanitize_file_path(file_path: str, config: ToolkitConfig) -> str:
    """
    Sanitize the file path to prevent directory traversal attacks.

    Args:
        file_path (str): The input file path.
        config (ToolkitConfig): The configuration instance.

    Returns:
        str: The sanitized absolute file path.

    Raises:
        ValueError: If the file path is not within allowed directories.
    """
    # Resolve the absolute path
    try:
        absolute_path = Path(file_path).resolve(strict=False)
    except Exception as e:
        logger.error(f"Error resolving file path '{file_path}': {e}")
        raise ValueError(f"Invalid file path: {e}")

    # Check if the path is within allowed directories
    allowed = False
    for dir_path in config.allowed_directories:
        try:
            allowed_dir = Path(dir_path).resolve(strict=False)
            if allowed_dir in absolute_path.parents or allowed_dir == absolute_path.parent:
                allowed = True
                break
        except Exception as e:
            logger.error(f"Error resolving allowed directory '{dir_path}': {e}")
            continue

    if not allowed:
        logger.error(f"Unauthorized file path access attempt: {absolute_path}")
        raise ValueError("Unauthorized file path.")

    return str(absolute_path)