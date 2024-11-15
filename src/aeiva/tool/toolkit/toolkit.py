# toolkit/toolkit.py

import importlib
import logging
import json
from typing import List, Any, Dict, Callable, Optional, Type, Tuple, get_origin, get_args, Union
from contextlib import asynccontextmanager, contextmanager
import asyncio
from pydantic import BaseModel

from aeiva.tool.tool import Tool
from aeiva.tool.toolkit.toolkit_config import ToolkitConfig
from aeiva.tool.toolkit.rbac import check_permission, PermissionError
from aeiva.tool.toolkit.security import sanitize_file_path
from aeiva.util.path_utils import snake_to_camel
from aeiva.util.os_utils import get_os_user


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Toolkit:
    """
    Toolkit class that manages multiple Tool instances, handles validation,
    enforces RBAC, and manages shared resources.
    """

    subclasses: Dict[str, Type['Toolkit']] = {}

    def __init_subclass__(cls, **kwargs):
        """
        Automatically register subclasses in the Toolkit's subclasses dictionary.
        """
        super().__init_subclass__(**kwargs)
        Toolkit.subclasses[cls.__name__] = cls

    def __init__(self, name: str, tool_names: List[str], config: Optional[ToolkitConfig] = None):
        """
        Initialize the Toolkit with a name, list of tool names, and optional configuration.

        Args:
            name (str): The name of the toolkit.
            tool_names (List[str]): The names of tools to be managed by the toolkit.
            config (Optional[ToolkitConfig]): Configuration for security and roles.
        """
        self.toolkit_name = name
        self.tool_names = tool_names
        self.config = config
        self.tools: Dict[str, Tool] = {}
        self.tool_schemas: Dict[str, Dict] = {}
        self.tool_models: Dict[str, Tuple[Type[BaseModel], Type[BaseModel]]] = {}
        self.shared_resources = None  # Placeholder for shared resources

        # Setup the toolkit
        self.setup()

    def setup(self):
        """
        Setup the toolkit by loading tools, their schemas, and initializing shared resources.
        """
        logger.info(f"Setting up toolkit '{self.toolkit_name}'.")

        # Load tools and their schemas
        for tool_name in self.tool_names:
            tool = Tool(api_name=tool_name)
            self.tools[tool_name] = tool
            schema = tool.load_tool_schema(tool_name)
            self.tool_schemas[tool_name] = schema
            logger.debug(f"Loaded schema for tool '{tool_name}': {schema}")

        # Load Pydantic models for validation
        self.load_pydantic_models_for_all_tools()

        # Initialize shared resources
        self.init_shared_resources()

    def load_pydantic_models_for_all_tools(self):
        """
        Load Pydantic models (Params and Result) for all tools for validation.
        """
        logger.info("Loading Pydantic models for all tools.")
        for tool_name in self.tool_names:
            try:
                param_model, result_model = self.load_pydantic_models_for_tool(tool_name)
                self.tool_models[tool_name] = (param_model, result_model)
                logger.debug(f"Loaded models for tool '{tool_name}': Params={param_model}, Result={result_model}")
            except Exception as e:
                logger.error(f"Failed to load models for tool '{tool_name}': {e}")
                raise

    def load_pydantic_models_for_tool(self, api_name: str) -> Tuple[Type[BaseModel], Type[BaseModel]]:
        """
        Load the parameter and result Pydantic models for the given API.

        Args:
            api_name (str): The name of the API function.

        Returns:
            Tuple[Type[BaseModel], Type[BaseModel]]: The parameter and result model classes.

        Raises:
            ValueError: If models cannot be loaded.
        """
        module_path = f"aeiva.tool.api.{api_name}.model"  # Adjusted as per user's path
        try:
            models_module = importlib.import_module(module_path)
            param_model_class = getattr(models_module, f"{snake_to_camel(api_name)}Params", None)
            result_model_class = getattr(models_module, f"{snake_to_camel(api_name)}Result", None)
            if not (param_model_class and issubclass(param_model_class, BaseModel)):
                logger.error(f"Param model class '{snake_to_camel(api_name)}Params' not found in '{module_path}'.")
                raise ValueError(f"Param model class '{snake_to_camel(api_name)}Params' not found in '{module_path}'.")
            if not (result_model_class and issubclass(result_model_class, BaseModel)):
                logger.error(f"Result model class '{snake_to_camel(api_name)}Result' not found in '{module_path}'.")
                raise ValueError(f"Result model class '{snake_to_camel(api_name)}Result' not found in '{module_path}'.")
            return param_model_class, result_model_class
        except ImportError as e:
            logger.error(f"Error importing models from '{module_path}': {e}")
            raise ImportError(f"Error importing models from '{module_path}': {e}")
        except AttributeError as e:
            logger.error(f"Error accessing model classes in '{module_path}': {e}")
            raise ValueError(f"Error accessing model classes in '{module_path}': {e}")

    def init_shared_resources(self):
        """
        Initialize shared resources required by the toolkit.
        Override this method in subclasses if needed.
        """
        logger.info("Initializing shared resources.")
        # Placeholder for initializing shared resources like databases, servers, etc.
        # Example:
        # self.shared_resources = initialize_database_connection()
        pass

    def teardown(self):
        """
        Teardown the toolkit by unloading tools, their schemas, and cleaning up shared resources.
        """
        logger.info(f"Tearing down toolkit '{self.toolkit_name}'.")

        # Clean up shared resources
        self.teardown_shared_resources()

        # Clear loaded data
        self.tools.clear()
        self.tool_schemas.clear()
        self.tool_models.clear()

    def teardown_shared_resources(self):
        """
        Teardown shared resources.
        Override this method in subclasses if needed.
        """
        logger.info("Tearing down shared resources.")
        # Placeholder for tearing down shared resources
        # Example:
        # if self.shared_resources:
        #     self.shared_resources.close()
        pass

    @asynccontextmanager
    async def acontext(self):
        """
        Asynchronous context manager to handle setup and teardown of shared resources.

        Usage:
            async with toolkit.acontent():
                # Execute tools
        """
        try:
            await self.asetup()
            yield self
        finally:
            await self.ateardown()

    @contextmanager
    def context(self):
        """
        Synchronous context manager to handle setup and teardown of shared resources.

        Usage:
            with toolkit.context():
                # Execute tools
        """
        try:
            self.setup()
            yield self
        finally:
            self.teardown()

    async def asetup(self):
        """
        Asynchronously setup shared resources.
        """
        logger.info(f"Asynchronously setting up toolkit '{self.toolkit_name}'.")
        # Override in subclasses if asynchronous setup is required
        pass

    async def ateardown(self):
        """
        Asynchronously teardown shared resources.
        """
        logger.info(f"Asynchronously tearing down toolkit '{self.toolkit_name}'.")
        # Override in subclasses if asynchronous teardown is required
        self.teardown()

    def execute(self, api_name: str, params: Dict[str, Any]) -> Any:
        """
        Synchronously execute a tool's API function with validation and RBAC checks.

        Args:
            api_name (str): The name of the API function to execute.
            params (Dict[str, Any]): The parameters for the API function.

        Returns:
            Any: The result of the tool execution.

        Raises:
            ValueError: If tool not found or parameter validation fails.
            PermissionError: If user does not have permission.
            RuntimeError: If tool execution fails.
        """
        tool = self.tools.get(api_name)
        if not tool:
            logger.error(f"Tool '{api_name}' not found in toolkit '{self.toolkit_name}'.")
            raise ValueError(f"Tool '{api_name}' not found in toolkit '{self.toolkit_name}'.")

        # Perform RBAC check if config is provided
        if self.config:
            # Automatically retrieve user role from OS
            os_user = get_os_user()
            user_role = self.config.user_role_mapping.get(os_user)
            if not user_role:
                logger.error(f"OS user '{os_user}' does not have an assigned role.")
                raise ValueError(f"OS user '{os_user}' does not have an assigned role.")
            if not check_permission(user_role, api_name, self.config):
                logger.error(f"User role '{user_role}' does not have permission to execute '{api_name}'.")
                raise PermissionError(f"User role '{user_role}' does not have permission to execute '{api_name}'.")

        # Load the Pydantic models for validation
        param_model, result_model = self.tool_models.get(api_name, (None, None))
        if not param_model or not result_model:
            logger.error(f"Pydantic models for tool '{api_name}' are not loaded.")
            raise ValueError(f"Pydantic models for tool '{api_name}' are not loaded.")

        # Instantiate and validate the parameter model
        try:
            param_instance = param_model(**params)
            logger.debug(f"Validated input parameters for '{api_name}': {param_instance}")
        except Exception as e:
            logger.error(f"Error parsing parameters for '{api_name}': {e}")
            raise ValueError(f"Invalid parameters for '{api_name}': {e}")

        # Perform security checks on parameters if needed
        param_instance = self.perform_security_checks(param_instance)

        # Execute the API function via the Tool
        try:
            raw_result = tool.execute(param_instance.dict())
            logger.debug(f"Raw result from '{api_name}': {raw_result}")
        except Exception as e:
            logger.error(f"Error executing tool '{api_name}': {e}")
            raise RuntimeError(f"Error executing tool '{api_name}': {e}")

        # Validate the result using the result model
        try:
            result_instance = result_model(**raw_result)
            logger.info(f"Execution of '{api_name}' successful with result: {result_instance}")
            return result_instance
        except Exception as e:
            logger.error(f"Error parsing result for '{api_name}': {e}")
            raise ValueError(f"Invalid result from '{api_name}': {e}")

    async def aexecute(self, api_name: str, params: Dict[str, Any]) -> Any:
        """
        Asynchronously execute a tool's API function with validation and RBAC checks.

        Args:
            api_name (str): The name of the API function to execute.
            params (Dict[str, Any]): The parameters for the API function.

        Returns:
            Any: The result of the tool execution.

        Raises:
            ValueError: If tool not found or parameter validation fails.
            PermissionError: If user does not have permission.
            RuntimeError: If tool execution fails.
        """
        tool = self.tools.get(api_name)
        if not tool:
            logger.error(f"Tool '{api_name}' not found in toolkit '{self.toolkit_name}'.")
            raise ValueError(f"Tool '{api_name}' not found in toolkit '{self.toolkit_name}'.")

        # Perform RBAC check if config is provided
        if self.config:
            # Automatically retrieve user role from OS
            os_user = get_os_user()
            user_role = self.config.user_role_mapping.get(os_user)
            if not user_role:
                logger.error(f"OS user '{os_user}' does not have an assigned role.")
                raise ValueError(f"OS user '{os_user}' does not have an assigned role.")
            if not check_permission(user_role, api_name, self.config):
                logger.error(f"User role '{user_role}' does not have permission to execute '{api_name}'.")
                raise PermissionError(f"User role '{user_role}' does not have permission to execute '{api_name}'.")

        # Load the Pydantic models for validation
        param_model, result_model = self.tool_models.get(api_name, (None, None))
        if not param_model or not result_model:
            logger.error(f"Pydantic models for tool '{api_name}' are not loaded.")
            raise ValueError(f"Pydantic models for tool '{api_name}' are not loaded.")

        # Instantiate and validate the parameter model
        try:
            param_instance = param_model(**params)
            logger.debug(f"Validated input parameters for '{api_name}': {param_instance}")
        except Exception as e:
            logger.error(f"Error parsing parameters for '{api_name}': {e}")
            raise ValueError(f"Invalid parameters for '{api_name}': {e}")

        # Perform security checks on parameters if needed
        param_instance = self.perform_security_checks(param_instance)

        # Execute the API function via the Tool
        try:
            raw_result = await tool.aexecute(param_instance.dict())
            logger.debug(f"Raw result from '{api_name}': {raw_result}")
        except Exception as e:
            logger.error(f"Error executing tool '{api_name}': {e}")
            raise RuntimeError(f"Error executing tool '{api_name}': {e}")

        # Validate the result using the result model
        try:
            result_instance = result_model(**raw_result)
            logger.info(f"Execution of '{api_name}' successful with result: {result_instance}")
            return result_instance
        except Exception as e:
            logger.error(f"Error parsing result for '{api_name}': {e}")
            raise ValueError(f"Invalid result from '{api_name}': {e}")

    def perform_security_checks(self, param_instance: BaseModel) -> BaseModel:
        """
        Perform security checks on parameters that require sanitization.

        Args:
            param_instance (BaseModel): The validated parameter instance.

        Returns:
            BaseModel: The sanitized parameter instance.

        Raises:
            ValueError: If sanitization fails for any field or if config is required but not provided.
        """
        sanitized_params = param_instance.dict()

        for field_name, field in param_instance.__fields__.items():
            sanitize = field.field_info.extra.get('sanitize', False)
            if not sanitize:
                continue  # Skip fields that do not require sanitization

            field_type = field.type_
            origin = get_origin(field_type)
            args = get_args(field_type)

            # Determine if the field is a string type or contains string types
            is_string_field = False

            if field_type == str:
                is_string_field = True
            elif origin is Union and str in args:
                is_string_field = True
            elif origin is list and len(args) == 1 and args[0] == str:
                is_string_field = True
            elif origin is Optional and str in args:
                is_string_field = True
            # Add more conditions here if there are other complex types containing strings

            if is_string_field:
                original_value = sanitized_params.get(field_name)
                if original_value is None:
                    continue  # Skip if the field value is None

                if self.config is None:
                    logger.error(
                        f"Configuration is required to sanitize field '{field_name}', "
                        f"but config is not provided."
                    )
                    raise ValueError(
                        f"Configuration is required to sanitize field '{field_name}', "
                        f"but config is not provided."
                    )

                try:
                    # If the field is a list of strings, sanitize each path individually
                    if origin is list and len(args) == 1 and args[0] == str:
                        if not isinstance(original_value, list):
                            logger.error(
                                f"Expected a list for field '{field_name}', "
                                f"got {type(original_value)}."
                            )
                            raise ValueError(
                                f"Expected a list for field '{field_name}'."
                            )
                        sanitized_list = []
                        for idx, item in enumerate(original_value):
                            sanitized_item = sanitize_file_path(item, self.config)
                            sanitized_list.append(sanitized_item)
                            logger.debug(
                                f"Sanitized '{field_name}[{idx}]': '{item}' -> '{sanitized_item}'"
                            )
                        sanitized_params[field_name] = sanitized_list
                    else:
                        # Sanitize single string path
                        sanitized_path = sanitize_file_path(original_value, self.config)
                        sanitized_params[field_name] = sanitized_path
                        logger.debug(
                            f"Sanitized '{field_name}': '{original_value}' -> '{sanitized_path}'"
                        )
                except ValueError as ve:
                    logger.error(
                        f"Sanitization failed for field '{field_name}': {ve}"
                    )
                    raise

        # Create a new instance of the parameter model with sanitized parameters
        sanitized_instance = param_instance.copy(update=sanitized_params)

        return sanitized_instance

    def generate_documentation(self) -> str:
        """
        Generate documentation for all functions managed by this toolkit based on their schemas.

        Returns:
            str: Generated documentation as a markdown string.
        """
        doc = f"# Toolkit: {self.toolkit_name}\n\n"
        for api_name, tool in self.tools.items():
            schema = self.tool_schemas.get(api_name, {})
            if not schema:
                continue
            doc += f"## Function: {api_name}\n\n"
            doc += f"**Description:** {schema.get('description', 'No description provided.')}\n\n"
            doc += "### Parameters:\n\n"
            parameters = schema.get("parameters", {})
            for prop, details in parameters.get("properties", {}).items():
                req = " (required)" if prop in parameters.get("required", []) else ""
                description = details.get("description", "")
                default = f" (default: {details.get('default')})" if "default" in details else ""
                doc += f"- **{prop}** ({details.get('type', 'any')}): {description}{default}{req}\n"
            doc += "\n### Example:\n\n"
            example = schema.get("example", "No example provided.")
            if isinstance(example, dict):
                example = json.dumps(example, indent=4)
            doc += f"```json\n{example}\n```\n\n"
        return doc