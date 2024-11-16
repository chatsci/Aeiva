# toolkit/system_toolkit/list_drives/api.py

import psutil
import platform
from typing import Dict, Any

def list_drives() -> Dict[str, Any]:
    """
    Lists all mounted drives or partitions.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        system = platform.system()
        partitions = psutil.disk_partitions(all=False)
        drives = []

        for partition in partitions:
            drive_info = {
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "opts": partition.opts
            }
            drives.append(drive_info)
        
        return {
            "output": {"drives": drives},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to list drives: {str(e)}",
            "error_code": "FAILED_TO_LIST_DRIVES"
        }