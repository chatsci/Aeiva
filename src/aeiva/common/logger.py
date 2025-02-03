# logger.py
import logging
import logging.config
from aeiva.util.file_utils import from_json_or_yaml


def setup_logging(
    config_file_path=None,
    log_file_path=None,
    verbose=False,
):
    """
    Loads logging config from 'config_file_path' (YAML or JSON) and sets up logging.
    Optionally override file handler's filename, and set root logger to DEBUG if 'verbose'.
    """
    config = from_json_or_yaml(config_file_path)

    # If user passed a custom file path for logs, override the "filename" in the config
    if log_file_path and "file_handler" in config["handlers"]:
        config["handlers"]["file_handler"]["filename"] = str(log_file_path)

    logging.config.dictConfig(config)

    # If --verbose was passed, raise the global level to DEBUG
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Return a logger for convenience (or you can omit this if you prefer)
    return logging.getLogger(__name__)