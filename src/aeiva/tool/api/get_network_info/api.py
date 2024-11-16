# toolkit/system_toolkit/get_network_info/api.py

import psutil
from typing import Dict, Any

def get_network_info() -> Dict[str, Any]:
    """
    Retrieves network information of the system.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        net_info = psutil.net_if_addrs()
        net_stats = psutil.net_if_stats()
        network_details = {}
        
        for interface, addrs in net_info.items():
            network_details[interface] = {
                "addresses": [addr.address for addr in addrs],
                "is_up": net_stats[interface].isup,
                "duplex": net_stats[interface].duplex.name if net_stats[interface].duplex else "UNKNOWN",
                "speed": net_stats[interface].speed,
                "mtu": net_stats[interface].mtu
            }
        
        return {
            "output": {"network_info": network_details},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"An unexpected error occurred: {str(e)}",
            "error_code": "UNEXPECTED_ERROR"
        }