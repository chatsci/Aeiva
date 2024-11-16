# toolkit/system_toolkit.py

from aeiva.tool.toolkit.toolkit import Toolkit

class SystemToolkit(Toolkit):
    """
    A toolkit for interacting with system-level operations.
    """

    def __init__(self, config=None):
        super().__init__(
            name="SystemToolkit",
            tool_names=[
                "get_system_info",
                "get_package_root",
                "get_user_home_path",
                "open_application",
                "close_application",
                "percept_terminal_input",
                "play_music",
                "stop_music",
                "take_screenshot"
                "list_processes",
                "kill_process",
                "monitor_process",
                "get_network_info",
                "check_internet_connection",
                "get_disk_usage",
                "clean_temp_files",
                "list_drives",
                "get_env_var",
                "set_env_var",
                "update_system_packages",
                "install_package",
                "create_user",
                "delete_user",
                "change_user_password",
                "view_system_logs",
                "monitor_system_resources",
            ],
            config=config
        )