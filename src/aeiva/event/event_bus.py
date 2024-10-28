# event_bus.py

import asyncio
import logging
import re
from functools import wraps
from typing import Callable, Dict, List, Any, Optional, Union
from aeiva.event.event import Event

# Configure logging
# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('event_bus')

class EventCancelled(Exception):
    """Exception to indicate that an event has been cancelled."""
    pass

class EventBus:
    """
    An asynchronous event bus for publishing and subscribing to events.

    Features:
    - Subscribers can use wildcard patterns to subscribe to multiple events.
    - Subscribers can cancel event propagation.
    - Subscribers can be set to auto-unsubscribe after one call.
    - Event-level prioritization in the queue.
    - Customizable error handling.
    - Logging for key actions.
    - emit, emit_after, and emit_only methods for flexible event emission.
    """

    def __init__(self):
        """
        Initializes the event bus.
        """
        self._subscribers: List[Dict] = []  # List of subscriber dictionaries
        self._event_queue = asyncio.PriorityQueue()
        self._processing_task: Optional[asyncio.Task] = None
        self._event_counter = 0  # Counter to maintain order of events with same priority
        self.loop = None

    def subscribe(
        self,
        event_pattern: str,
        callback: Callable[[Event], Any],
        *,
        priority: int = 0,
        once: bool = False
    ):
        """
        Subscribes a callback function to events matching a pattern.

        Args:
            event_pattern (str): The event name or pattern to subscribe to.
            callback (Callable[[Event], Any]): The callback function.
            priority (int, optional): Priority of the callback.
            once (bool, optional): If True, unsubscribe after one call.
        """
        subscriber = {
            'pattern': re.compile(event_pattern.replace('*', '.*')),
            'callback': callback,
            'priority': priority,
            'once': once
        }
        self._subscribers.append(subscriber)
        logger.info(f"Subscribed '{callback.__name__}' to pattern '{event_pattern}' with priority {priority}.")

    def unsubscribe(self, callback: Callable[[Event], Any]):
        """
        Unsubscribes a callback function from all events.

        Args:
            callback (Callable[[Event], Any]): The callback function to remove.
        """
        self._subscribers = [
            sub for sub in self._subscribers
            if sub['callback'] != callback
        ]
        logger.info(f"Unsubscribed '{callback.__name__}' from all events.")

    async def publish(self, event: Event, only: Union[str, List[str]] = None):
        """
        Publishes an event to the event bus.

        Args:
            event (Event): The event to publish.
            only (str or List[str], optional): Names of specific subscribers to notify.
        """
        self._event_counter += 1
        # Use a tuple of (priority, counter) to ensure proper ordering
        await self._event_queue.put((event.priority * -1, self._event_counter, event, only))
        logger.info(f"Published event '{event.name}' with priority {event.priority}.")

    async def _process_events(self):
        """
        Internal coroutine that processes events from the queue and dispatches them to subscribers.
        """
        while True:
            try:
                _, _, event, only = await self._event_queue.get()
                logger.info(f"Processing event '{event.name}'.")
                await self._dispatch_event(event, only)
                self._event_queue.task_done()
            except asyncio.CancelledError:
                # Exit the loop gracefully
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                self._event_queue.task_done()

    async def _dispatch_event(self, event: Event, only: Union[str, List[str]] = None):
        """
        Dispatches an event to the appropriate subscribers.

        Args:
            event (Event): The event to dispatch.
            only (str or List[str], optional): Names of specific subscribers to notify.
        """
        subscribers = sorted(
            [
                sub for sub in self._subscribers
                if sub['pattern'].fullmatch(event.name)
                and (only is None or sub['callback'].__name__ in (only if isinstance(only, list) else [only]))
            ],
            key=lambda x: x['priority'],
            reverse=True
        )
        for subscriber in subscribers:
            callback = subscriber['callback']
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    await asyncio.get_event_loop().run_in_executor(None, callback, event)
            except EventCancelled:
                logger.info(f"Event '{event.name}' cancelled by '{callback.__name__}'.")
                break  # Stop further propagation
            except Exception as e:
                logger.error(f"Error in callback '{callback.__name__}' for event '{event.name}': {e}")
                self._handle_callback_exception(e, callback, event)
            finally:
                if subscriber.get('once'):
                    self.unsubscribe(callback)

    def _handle_callback_exception(self, exception, callback, event):
        """
        Handle exceptions raised by subscriber callbacks.

        Args:
            exception (Exception): The exception raised.
            callback (Callable): The subscriber callback.
            event (Event): The event being processed.
        """
        # Default behavior is to log the exception.
        pass  # Can be customized as needed.

    def start(self):
        """
        Starts the event bus processing loop.
        """
        if self._processing_task is None:
            self.loop = asyncio.get_running_loop()
            self._processing_task = asyncio.create_task(self._process_events())
            logger.info("Event bus started.")

    def stop(self):
        """
        Stops the event bus processing loop.
        """
        if self._processing_task:
            self._processing_task.cancel()
            logger.info("Event bus stopped.")

    def on(self, event_pattern: str, priority: int = 0, once: bool = False):
        """
        Decorator for subscribing a function to events matching a pattern.

        Usage:
            @event_bus.on('event.*', priority=10)
            async def handler(event):
                ...

        Args:
            event_pattern (str): The event name or pattern to subscribe to.
            priority (int, optional): Priority of the callback.
            once (bool, optional): If True, unsubscribe after one call.

        Returns:
            Callable: The decorator function.
        """
        def decorator(callback: Callable[[Event], Any]):
            self.subscribe(event_pattern, callback, priority=priority, once=once)
            return callback
        return decorator

    def emit_after(self, event_name: str, priority: int = 0):
        """
        Decorator that emits an event after the decorated function is called.

        Usage:
            @event_bus.emit_after('event_name')
            def some_function():
                ...

        Args:
            event_name (str): The name of the event to emit after function execution.
            priority (int, optional): The priority of the event.

        Returns:
            Callable: The decorator function.
        """
        def decorator(func: Callable):
            if asyncio.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    result = await func(*args, **kwargs)
                    await self.emit(event_name, priority=priority)
                    return result
                return async_wrapper
            else:
                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    result = func(*args, **kwargs)
                    asyncio.create_task(self.emit(event_name, priority=priority))
                    return result
                return sync_wrapper
        return decorator

    async def emit(self, event_name: str, payload: Any = None, priority: int = 0):
        """
        Emits an event to all matching subscribers.

        Args:
            event_name (str): The name of the event to emit.
            payload (Any, optional): The payload of the event.
            priority (int, optional): The priority of the event.
        """
        await self.publish(Event(name=event_name, payload=payload, priority=priority))

    async def emit_only(self, event_name: str, subscriber_names: Union[str, List[str]], payload: Any = None, priority: int = 0):
        """
        Emits an event only to specified subscribers.

        Args:
            event_name (str): The name of the event to emit.
            subscriber_names (str or List[str]): The name(s) of subscribers to notify.
            payload (Any, optional): The payload of the event.
            priority (int, optional): The priority of the event.
        """
        await self.publish(Event(name=event_name, payload=payload, priority=priority), only=subscriber_names)

    async def wait_until_all_events_processed(self):
        """
        Waits until all events in the queue have been processed.
        """
        await self._event_queue.join()