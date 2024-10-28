import asyncio
import reactivex as rx
from reactivex import operators as ops
from typing import Callable, Any, AsyncIterable, Union, Dict, Optional
import logging
from aeiva.action.tool.tool import Tool


class Sensor:
    """
    A class representing a sensor that captures input data and converts it into a reactive stream.
    """

    def __init__(self, api_name: str, api_params: Optional[Dict[str, Any]]=None):
        self.api_name = api_name  # We put the sensor functions in api module now.
        self.api_params = api_params or {}

        function_module = f"aeiva.action.tool.api.function.{self.api_name}.api"
        func = __import__(function_module, fromlist=[self.api_name])
        function: Callable = getattr(func, self.api_name)
        self.sensor_function = function
        # TODO: add other fields later, like name, modularity, type, etc. See Signal fields.
        
    def percept(self):
        return rx.from_iterable(self.sensor_function(**self.api_params))  # Return an observable from the generator

# import inspect
# import reactivex as rx
# from reactivex import Observable
# import asyncio


# def observable_from_async_generator(async_gen):
#     def on_subscribe(observer, scheduler):
#         async def run():
#             try:
#                 async for item in async_gen:
#                     observer.on_next(item)
#                 observer.on_completed()
#             except Exception as e:
#                 observer.on_error(e)
#         # Schedule the async generator to run in the event loop
#         asyncio.create_task(run())
#     return rx.create(on_subscribe)


# class Sensor:
#     """
#     A class representing a sensor that captures input data and converts it into a reactive stream.
#     """

#     def __init__(self, api_name: str, api_params: Optional[Dict[str, Any]] = None):
#         self.api_name = api_name
#         self.api_params = api_params or {}

#         function_module = f"aeiva.action.tool.api.function.{self.api_name}.api"
#         func = __import__(function_module, fromlist=[self.api_name])
#         function: Callable = getattr(func, self.api_name)
#         self.sensor_function = function

#     def percept(self):
#         result = self.sensor_function(**self.api_params)

#         if inspect.isasyncgen(result):
#             # If the result is an async generator
#             return observable_from_async_generator(result)
#         elif inspect.isgenerator(result):
#             # If the result is a synchronous generator
#             return rx.from_iterable(result)
#         else:
#             # If the result is not a generator, check if it's a coroutine
#             if asyncio.iscoroutine(result):
#                 # If it's a coroutine, await it and emit the result
#                 async def single_value():
#                     value = await result
#                     yield value
#                 return observable_from_async_generator(single_value())
#             else:
#                 # Not a coroutine or generator, treat as a single value
#                 return rx.just(result)