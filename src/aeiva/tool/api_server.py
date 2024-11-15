# src/aeiva/tool/api_server.py

from fastapi import FastAPI, Request, HTTPException
from pathlib import Path
import importlib.util
import logging
from inspect import signature, Parameter
import json
import asyncio

app = FastAPI()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Define the base directory relative to this script
BASE_DIR = Path(__file__).resolve().parent

def load_api_module(api_name: str):
    """
    Dynamically load the API module for the given api_name.

    Args:
        api_name (str): The name of the API.

    Returns:
        module: The loaded API module.

    Raises:
        FileNotFoundError: If the API module does not exist.
        ImportError: If the module cannot be imported.
    """
    # Construct the path to the API module
    api_path = BASE_DIR / "api" / api_name / "api.py"

    if not api_path.exists():
        logger.error(f"API module not found at path: {api_path}")
        raise FileNotFoundError(f"API module not found at path: {api_path}")

    module_name = f"aeiva.tool.api.{api_name}.api"
    spec = importlib.util.spec_from_file_location(module_name, str(api_path))
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        logger.info(f"Successfully loaded module '{module_name}'")
    except Exception as e:
        logger.error(f"Failed to load module '{module_name}': {e}")
        raise ImportError(f"Failed to load module '{module_name}': {e}")
    return module

@app.get("/")
async def root():
    """
    Root endpoint to confirm the API server is running.
    """
    return {"message": "Welcome to the AI Agent API system!"}

@app.get("/api/{api_name}/{action_name}")
async def call_api_action(api_name: str, action_name: str, request: Request):
    """
    Endpoint to dynamically call an action within a specified API.

    Args:
        api_name (str): The name of the API.
        action_name (str): The name of the action/function to execute.
        request (Request): The incoming HTTP request.

    Returns:
        dict: The result of the action or an error message.
    """
    try:
        logger.info(f"Starting call_api_action for API '{api_name}', Action '{action_name}'")

        # Load the API module
        module = load_api_module(api_name)

        # Retrieve the action function
        try:
            action = getattr(module, action_name)
            logger.info(f"Retrieved action '{action_name}' from API '{api_name}'")
        except AttributeError:
            logger.error(f"Action '{action_name}' not found in API '{api_name}'")
            raise HTTPException(status_code=404, detail=f"Action '{action_name}' not found in API '{api_name}'")

        # Extract parameters based on request method
        params = {}
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                params = await request.json()
                logger.info(f"Received JSON payload: {params}")
            except json.JSONDecodeError:
                logger.error("Invalid JSON payload")
                raise HTTPException(status_code=400, detail="Invalid JSON payload")
        else:
            # For GET requests, extract query parameters
            params = dict(request.query_params)
            logger.info(f"Received query parameters: {params}")

        # Get the function signature
        sig = signature(action)
        logger.info(f"Function signature for '{action_name}': {sig}")

        # Prepare to collect converted parameters
        converted_params = {}

        for param_name, param in sig.parameters.items():
            if param_name in params:
                value = params[param_name]
                param_type = param.annotation if param.annotation != Parameter.empty else str
                try:
                    if param_type == bool:
                        # Convert to boolean
                        if isinstance(value, bool):
                            converted_value = value
                        elif isinstance(value, str):
                            converted_value = value.lower() in ("true", "1", "yes")
                        else:
                            converted_value = bool(value)
                    elif param_type in [int, float, str]:
                        converted_value = param_type(value)
                    elif param_type == list or param_type == dict:
                        converted_value = json.loads(value)
                    else:
                        # For more complex types, assume Pydantic models or custom parsing
                        converted_value = param_type(value)
                    converted_params[param_name] = converted_value
                    logger.debug(f"Converted parameter '{param_name}': {converted_value} (Type: {param_type})")
                except (ValueError, json.JSONDecodeError, TypeError) as e:
                    logger.error(f"Invalid value for parameter '{param_name}': {value} ({e})")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid value for parameter '{param_name}': {value}. Expected type {param_type.__name__}."
                    )
            else:
                if param.default == Parameter.empty:
                    logger.error(f"Missing required parameter: {param_name}")
                    raise HTTPException(status_code=400, detail=f"Missing required parameter: {param_name}")
                else:
                    # Use default value
                    converted_params[param_name] = param.default
                    logger.debug(f"Using default value for parameter '{param_name}': {param.default}")

        # Determine if the action is asynchronous
        if asyncio.iscoroutinefunction(action):
            logger.info(f"Action '{action_name}' is asynchronous. Awaiting execution.")
            result = await action(**converted_params)
        else:
            logger.info(f"Action '{action_name}' is synchronous. Executing directly.")
            result = action(**converted_params)

        logger.info(f"Action '{action_name}' executed successfully with result: {result}")
        return {"result": result}

    except FileNotFoundError as e:
        logger.error(f"API module not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException as he:
        # Re-raise HTTP exceptions to be handled by FastAPI
        raise he
    except Exception as e:
        logger.error(f"Unhandled exception in call_api_action: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)