# toolkit/system_toolkit/install_package/api.py

import subprocess
import platform
from typing import Dict, Any

def install_package(package_name: str, package_type: str = "python") -> Dict[str, Any]:
    """
    Installs a specified system or Python package.

    Args:
        package_name (str): The name of the package to install.
        package_type (str, optional): Type of package ("python" or "system"). Defaults to "python".

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        system = platform.system()
        if package_type == "python":
            command = ["pip", "install", package_name]
        elif package_type == "system":
            if system == "Windows":
                # Using winget for Windows
                command = ["winget", "install", package_name]
            elif system == "Darwin":
                # Using brew for macOS
                command = ["brew", "install", package_name]
            elif system == "Linux":
                distro = platform.linux_distribution()[0].lower()
                if 'ubuntu' in distro or 'debian' in distro:
                    command = ["sudo", "apt-get", "install", "-y", package_name]
                elif 'fedora' in distro or 'centos' in distro or 'redhat' in distro:
                    command = ["sudo", "dnf", "install", "-y", package_name]
                else:
                    return {
                        "output": None,
                        "error": f"Unsupported Linux distribution: {distro}",
                        "error_code": "UNSUPPORTED_DISTRIBUTION"
                    }
            else:
                return {
                    "output": None,
                    "error": f"Unsupported operating system: {system}",
                    "error_code": "UNSUPPORTED_OS"
                }
        else:
            return {
                "output": None,
                "error": f"Unsupported package type: {package_type}",
                "error_code": "UNSUPPORTED_PACKAGE_TYPE"
            }
        
        # Execute the command
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            return {
                "output": result.stdout,
                "error": None,
                "error_code": "SUCCESS"
            }
        else:
            return {
                "output": result.stdout,
                "error": result.stderr,
                "error_code": "FAILED_TO_INSTALL_PACKAGE"
            }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to install package '{package_name}': {str(e)}",
            "error_code": "FAILED_TO_INSTALL_PACKAGE"
        }