# toolkit/system_toolkit/monitor_process/api.py

import psutil
from typing import Dict, Any

def monitor_process(process_identifier: str) -> Dict[str, Any]:
    """
    Monitors the status or resource usage of a specific process by PID or name.

    Args:
        process_identifier (str): The PID (as string) or name of the process to monitor.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        process_info = []
        if process_identifier.isdigit():
            pid = int(process_identifier)
            try:
                proc = psutil.Process(pid)
                info = {
                    "pid": proc.pid,
                    "name": proc.name(),
                    "status": proc.status(),
                    "cpu_percent": proc.cpu_percent(interval=1.0),
                    "memory_percent": proc.memory_percent(),
                }
                process_info.append(info)
            except psutil.NoSuchProcess:
                return {
                    "output": None,
                    "error": f"No process found with PID {pid}.",
                    "error_code": "PROCESS_NOT_FOUND"
                }
        else:
            # Assume it's a process name
            found = False
            for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_percent']):
                if proc.info['name'] and proc.info['name'].lower() == process_identifier.lower():
                    info = {
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "status": proc.info['status'],
                        "cpu_percent": proc.info['cpu_percent'],
                        "memory_percent": proc.info['memory_percent'],
                    }
                    process_info.append(info)
                    found = True
            if not found:
                return {
                    "output": None,
                    "error": f"No process found with name '{process_identifier}'.",
                    "error_code": "PROCESS_NOT_FOUND"
                }
        
        return {
            "output": {"process_info": process_info},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to monitor process '{process_identifier}': {str(e)}",
            "error_code": "FAILED_TO_MONITOR_PROCESS"
        }