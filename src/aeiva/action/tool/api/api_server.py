# api/api_server.py

from fastapi import FastAPI, Request
import os
import importlib.util
import logging
from inspect import signature
import json

app = FastAPI()

# Get the absolute path of the current script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Utility function to dynamically import a module
def load_api_module(api_name: str):
    api_path = os.path.join(BASE_DIR, "api_tools", api_name, "api.py")
    spec = importlib.util.spec_from_file_location(f"api_tools.{api_name}.api", api_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

@app.get("/")
async def root():
    return {"message": "Welcome to the AI Agent API system!"}

# Configure logging
logging.basicConfig(level=logging.INFO)

@app.get("/api/{api_name}/{action_name}")
async def call_api_action(api_name: str, action_name: str, request: Request):
    try:
        print("start try call_api_function")
        module = load_api_module(api_name)
        action = getattr(module, action_name)

        # Extract query parameters from the request
        params = dict(request.query_params)
        # Log the parameters for debugging
        logging.info(f"Received parameters: {params}")
        print("Received parameters: ", params)

        # Get the function signature
        sig = signature(action)
        logging.info(f"Function signature: {sig}")

        # Convert parameter values to appropriate types
        converted_params = {}
        for param_name, param in sig.parameters.items():
            if param_name in params:
                value = params[param_name]
                # Convert the value to the appropriate type
                param_type = param.annotation if param.annotation != param.empty else str
                try:
                    if param_type == param.empty:
                        converted_value = value  # No type conversion
                    elif param_type in [list, dict]:
                        converted_value = json.loads(value)
                    else:
                        converted_value = param_type(value)
                    converted_params[param_name] = converted_value
                except (ValueError, json.JSONDecodeError) as e:
                    return {"error": f"Invalid value for parameter '{param_name}': {value} is not of type {param_type.__name__}"}
            else:
                if param.default == param.empty:
                    # Missing required parameter
                    return {"error": f"Missing required parameter: {param_name}"}

        # Call the action with the converted parameters
        result = action(**converted_params)
        return {"result": result}
    except AttributeError:
        return {"error": f"Action '{action_name}' not found in API '{api_name}'"}
    except TypeError as e:
        return {"error": f"TypeError: {str(e)}"}
    except Exception as e:
        logging.error(f"Exception in call_api_action: {e}", exc_info=True)
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)