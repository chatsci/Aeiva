# EventBus Library

A powerful, flexible, and asynchronous event bus library for Python applications.

## Features

- **Asynchronous Event Processing**: Leveraging `asyncio` for efficient event handling.
- **Priority-Based Event Dispatching**: Events and subscribers can have priorities.
- **Wildcard Event Subscriptions**: Subscribe to multiple events using patterns.
- **Synchronous and Asynchronous Callbacks**: Support for both sync and async subscriber functions.
- **Event Cancellation**: Ability to stop event propagation.
- **Once-Only Subscriptions**: Subscribers can auto-unsubscribe after one event.
- **Emit Methods**: Flexible event emission with `emit`, `emit_after`, and `emit_only`.
- **Logging and Monitoring**: Built-in logging for monitoring event flow.

## Installation

Include `event.py` and `event_bus.py` in your project directory.

## Usage

### Importing the EventBus

```python
from event_bus import EventBus, EventCancelled
```

### Creating an EventBus Instance

```python
event_bus = EventBus()
event_bus.start()
```

### Subscribing to Events

Using the subscribe Method

```python
def handler(event):
    print(f"Received event: {event.name}")

event_bus.subscribe('my_event', handler)
```

Using the @on Decorator

```python
@event_bus.on('my_event', priority=10)
def decorated_handler(event):
    print(f"Received event: {event.name} with priority 10")
```

Wildcard Subscriptions

```python
@event_bus.on('user.*')
def user_event_handler(event):
    print(f"User event: {event.name}")
```

Once-Only Subscriptions

```python
@event_bus.on('init', once=True)
def init_handler(event):
    print("Initialization complete")
```

### Emitting Events

Emitting an Event

```python
await event_bus.emit('my_event', payload={'key': 'value'}, priority=5)
```

Emitting an Event Only to Specific Subscribers

```python
await event_bus.emit_only('my_event', subscriber_names='decorated_handler', payload={'key': 'value'})
```

Emitting an Event After a Function Executes

```python
@event_bus.emit_after('post_function_event')
def some_function():
    print("Function executed")
```

###  Subscribe to the post-function event

```python
@event_bus.on('post_function_event')
def post_handler(event):
    print("Post function event received")
```

### Cancelling Event Propagation

```python
@event_bus.on('critical_event')
def canceling_handler(event):
    print("Cancelling event propagation")
    raise EventCancelled()
```

### Unsubscribing from Events

```python
event_bus.unsubscribe(handler)
```

### Stopping the EventBus

```python
await event_bus.wait_until_all_events_processed()
event_bus.stop()
```

### Example

See example_usage.py for a comprehensive example demonstrating all features.

---
*© 2024 Bang Liu - All Rights Reserved. This source code is licensed under the license found in the LICENSE file in the root directory of this source tree.*