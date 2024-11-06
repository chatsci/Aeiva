#!/usr/bin/env python
import asyncio
import time
from functools import wraps
from typing import Callable, Union


def retry_sync(max_attempts: Union[int, Callable], backoff_factor: Union[float, Callable], exceptions: tuple):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            attempts = 0
            max_attempts_val = max_attempts(self) if callable(max_attempts) else max_attempts
            backoff_factor_val = backoff_factor(self) if callable(backoff_factor) else backoff_factor
            wait_time = backoff_factor_val
            while attempts < max_attempts_val:
                try:
                    return func(self, *args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    if attempts == max_attempts_val:
                        raise e
                    time.sleep(wait_time)
                    wait_time *= 2
        return wrapper
    return decorator


def retry_async(max_attempts: Union[int, Callable], backoff_factor: Union[float, Callable], exceptions: tuple):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            attempts = 0
            max_attempts_val = max_attempts(self) if callable(max_attempts) else max_attempts
            backoff_factor_val = backoff_factor(self) if callable(backoff_factor) else backoff_factor
            wait_time = backoff_factor_val
            while attempts < max_attempts_val:
                try:
                    return await func(self, *args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    if attempts == max_attempts_val:
                        raise e
                    await asyncio.sleep(wait_time)
                    wait_time *= 2
        return wrapper
    return decorator