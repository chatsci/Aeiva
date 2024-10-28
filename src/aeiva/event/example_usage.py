# example_usage.py

import asyncio
from event_bus import EventBus, EventCancelled

async def main():
    # Create an instance of EventBus and start it
    event_bus = EventBus()
    event_bus.start()

    # Example synchronous callback
    def sync_handler(event):
        print(f"[Sync Handler] Received event: {event.name} with payload: {event.payload}")

    # Example asynchronous callback
    async def async_handler(event):
        await asyncio.sleep(0.1)  # Simulate async operation
        print(f"[Async Handler] Received event: {event.name} with payload: {event.payload}")

    # Subscribe using method
    event_bus.subscribe('test_event', sync_handler)

    # Subscribe using decorator with higher priority
    @event_bus.on('test_event', priority=10)
    async def decorated_async_handler(event):
        print(f"[Decorated Async Handler] Received event: {event.name} with payload: {event.payload}")

    # Subscribe another handler with different priority
    @event_bus.on('test_event', priority=5)
    def high_priority_sync_handler(event):
        print(f"[High Priority Sync Handler] Received event: {event.name} with payload: {event.payload}")

    # Subscribe using names to demonstrate emit_only
    @event_bus.on('test_event')
    def named_handler(event):
        print(f"[Named Handler] Received event: {event.name} with payload: {event.payload}")

    # Subscribe with 'once' to auto-unsubscribe after one call
    @event_bus.on('test.once', once=True)
    def once_handler(event):
        print(f"[Once Handler] Received event: {event.name}. This handler will now unsubscribe.")

    # Subscribe to all events using wildcard
    @event_bus.on('test.*')
    async def wildcard_handler(event):
        print(f"[Wildcard Handler] Received event: {event.name} with payload: {event.payload}")

    # Subscribe to a specific event with cancellation
    @event_bus.on('test.cancel', priority=5)
    async def canceling_handler(event):
        print(f"[Canceling Handler] Cancelling event: {event.name}")
        raise EventCancelled()

    # Subscribe to an event and raise an exception
    @event_bus.on('test.error')
    def error_handler(event):
        print(f"[Error Handler] About to raise an exception.")
        raise ValueError("An error occurred in the handler.")

    # Demonstrate emit_after
    @event_bus.emit_after('post_function_event')
    def some_function():
        print("[Some Function] Function is running.")

    # Subscribe to the event emitted after function execution
    @event_bus.on('post_function_event')
    def post_function_handler(event):
        print(f"[Post Function Handler] Received event: {event.name}")

    # Emit events
    await event_bus.emit('test_event', payload={'data': 'Hello World!'})

    # Emit only to specific subscribers
    await event_bus.emit_only('test_event', subscriber_names='named_handler', payload={'data': 'Only Named Handler'})

    # Call the function decorated with emit_after
    some_function()

    # Unsubscribe a handler
    event_bus.unsubscribe(sync_handler)

    # Publish another event to show that sync_handler has been unsubscribed
    await event_bus.emit('test_event', payload={'data': 'Second Event'})

    # Emit events to demonstrate once-only subscription
    await event_bus.emit('test.once', payload={'data': 'First Call'})
    await event_bus.emit('test.once', payload={'data': 'Second Call'})

    # Emit event that will be cancelled
    await event_bus.emit('test.cancel', payload={'data': 'This will be cancelled'})

    # Emit event that will cause an error in handler
    await event_bus.emit('test.error', payload={'data': 'This will cause an error'})

    # Emit different event
    await event_bus.emit('another_event', payload={'info': 'Different event data'})

    # Wait until all events are processed
    await event_bus.wait_until_all_events_processed()

    # Stop the event bus
    event_bus.stop()

if __name__ == '__main__':
    asyncio.run(main())