import os
import sys
import platform
import importlib.util
from pathlib import Path
import logging

# Configure logging for the module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_package_root(package_name: str) -> str:
    """
    Obtain the root directory of a given package.

    Args:
        package_name (str): The name of the package.

    Returns:
        str: The absolute path to the package root directory.
    """
    spec = importlib.util.find_spec(package_name)
    if spec is None or spec.origin is None:
        raise ImportError(f"Cannot find package '{package_name}'")
    package_path = os.path.dirname(os.path.abspath(spec.origin))
    return package_path


def get_user_home_path() -> Path:
    """
    Retrieves the home directory of the current user across different platforms.

    Supported Platforms:
        - Windows
        - macOS
        - Linux
        - iOS (best-effort)
        - Android (best-effort)

    Returns:
        Path: A `Path` object representing the user's home directory.

    Raises:
        EnvironmentError: If the home directory cannot be determined.
    """
    system = platform.system()
    logger.info(f"Detected operating system: {system}")

    try:
        if system == "Windows":
            # Windows: Use USERPROFILE or combine HOMEDRIVE and HOMEPATH
            home = os.environ.get('USERPROFILE') or os.path.join(os.environ.get('HOMEDRIVE', ''), os.environ.get('HOMEPATH', ''))
            logger.debug(f"Windows home directory: {home}")
        elif system in ["Linux", "Darwin"]:  # Darwin is macOS
            # Unix-like systems: Use expanduser
            home = os.path.expanduser("~")
            logger.debug(f"Unix-like home directory: {home}")
        elif system == "Java":  # Potentially Android (e.g., running via Jython or similar)
            # Android typically uses /data/user/0/<package_name>/ or /sdcard/
            # However, accessing these paths may require specific permissions
            # Here, we attempt to use the HOME environment variable
            home = os.environ.get('HOME') or '/sdcard/'
            logger.debug(f"Android home directory (best-effort): {home}")
        elif system == "iOS":
            # iOS applications are sandboxed; home directory is typically the app's sandbox
            # Accessing it might require specific APIs or configurations
            # Here, we return the current working directory as a placeholder
            home = Path.cwd()
            logger.debug(f"iOS home directory (best-effort): {home}")
        else:
            # Fallback for unknown systems
            home = os.path.expanduser("~")
            logger.warning(f"Unknown system '{system}'. Falling back to expanduser: {home}")

        if home and os.path.isdir(home):
            return Path(home)
        else:
            raise EnvironmentError("Determined home directory does not exist or is not a directory.")
    
    except Exception as e:
        logger.error(f"Failed to determine the user's home directory: {e}")
        raise EnvironmentError("Cannot determine the user's home directory.") from e

def snake_to_camel(snake_str: str) -> str:
    """
    Convert a snake_case string to CamelCase.

    Args:
        snake_str (str): The snake_case string.

    Returns:
        str: The CamelCase string.
    """
    components = snake_str.split('_')
    # Capitalize the first letter of each component
    return ''.join(x.title() for x in components)