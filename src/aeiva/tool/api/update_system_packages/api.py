# toolkit/system_toolkit/update_system_packages/api.py

import subprocess
import platform
from typing import Dict, Any

def update_system_packages() -> Dict[str, Any]:
    """
    Initiates system package updates.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        system = platform.system()
        if system == "Windows":
            # Using winget for Windows package management
            command = ["winget", "upgrade", "--all"]
        elif system == "Darwin":
            # Using brew for macOS
            command = ["brew", "update", "&&", "brew", "upgrade"]
        elif system == "Linux":
            distro = platform.linux_distribution()[0].lower()
            if 'ubuntu' in distro or 'debian' in distro:
                command = ["sudo", "apt-get", "update", "&&", "sudo", "apt-get", "upgrade", "-y"]
            elif 'fedora' in distro or 'centos' in distro or 'redhat' in distro:
                command = ["sudo", "dnf", "upgrade", "-y"]
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
        
        # Execute the command
        result = subprocess.run(' '.join(command), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
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
                "error_code": "FAILED_TO_UPDATE_PACKAGES"
            }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to update system packages: {str(e)}",
            "error_code": "FAILED_TO_UPDATE_PACKAGES"
        }