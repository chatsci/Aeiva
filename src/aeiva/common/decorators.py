# decorators.py

from typing import Callable
import importlib
import pkgutil


# OPERATOR_TYPES is a list of the different kinds of operations we want to create decorators for.
# These could be specific tasks or steps in your data pipeline, like "model_initializer", "data_loader", etc.
OPERATOR_TYPES = [
    "resource_preparer",
    "data_formatter",
    "data_processor",
    "data_loader",
    "data_filter",
    "data_sampler",
    "model_loader",
    "model_initializer", 
    "dataitem_processor",
    "trainer",
    "evaluator",
    "inferer"
]

# OPERATORS is a dictionary mapping from each operator type to another dictionary, 
# which will map specific names to the functions decorated with the corresponding decorator.
# This provides a way to retrieve these functions later, using their operator type and name.
OPERATORS = {operator_type: {} for operator_type in OPERATOR_TYPES}


def import_submodules(package, recursive=True):
    """ Import all submodules of a module, recursively, including subpackages """

    if isinstance(package, str):
        package = importlib.import_module(package)

    results = {}

    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_name = package.__name__ + "." + name
        results[full_name] = importlib.import_module(full_name)
        if recursive and is_pkg:
            results.update(import_submodules(full_name))

    return results


def create_decorator(operator_type: str):
    register = OPERATORS[operator_type]

    def decorator(name: str):
        def inner(func: Callable):
            register[name] = func
            return func
        return inner

    return decorator


# Create specific decorators for each operator type
# These decorators can be used to register functions for each corresponding operation.
register_resource_preparer = create_decorator("resource_preparer")
register_data_formatter = create_decorator("data_formatter")
register_data_loader = create_decorator("data_loader")
register_data_processor = create_decorator("data_processor")
register_data_filter = create_decorator("data_filter")
register_data_sampler = create_decorator("data_sampler")
register_model_loader = create_decorator("model_loader")
register_model_initializer = create_decorator("model_initializer")
register_dataitem_processor = create_decorator("dataitem_processor")
register_trainer = create_decorator("trainer")
register_evaluator = create_decorator("evaluator")
register_inferer = create_decorator("inferer")

# # Import all submodules where decorated functions could be located
# import_submodules('aeiva')  # Replace 'aeiva' with the actual package name
