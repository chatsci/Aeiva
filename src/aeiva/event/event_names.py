"""
EventNames: Central registry of event name constants.

Using constants instead of magic strings:
1. Enables IDE autocomplete and refactoring
2. Catches typos at import time, not runtime
3. Documents all events in one place

Usage:
    from aeiva.event.event_names import EventNames

    await event_bus.emit(EventNames.PERCEPTION_OUTPUT, payload=data)
    event_bus.subscribe(EventNames.COGNITION_THOUGHT, handler)
"""


class EventNames:
    """Central registry of all event names used in AEIVA."""

    # ═══════════════════════════════════════════════════════════════════
    # PERCEPTION EVENTS
    # ═══════════════════════════════════════════════════════════════════
    PERCEPTION_STIMULI = "perception.stimuli"
    PERCEPTION_GRADIO = "perception.gradio"
    PERCEPTION_REALTIME = "perception.realtime"
    PERCEPTION_API = "perception.api"
    PERCEPTION_OUTPUT = "perception.output"
    PERCEPTION_TERMINAL = "perception.terminal"
    PERCEPTION_SLACK = "perception.slack"
    PERCEPTION_WHATSAPP = "perception.whatsapp"
    PERCEPTION_MAID = "perception.maid"
    PERCEPTION_AUDIO_CHUNK = "perception.audio_chunk"
    PERCEPTION_VIDEO_FRAME = "perception.video_frame"

    # ═══════════════════════════════════════════════════════════════════
    # COGNITION EVENTS
    # ═══════════════════════════════════════════════════════════════════
    COGNITION_THINK = "cognition.think"
    COGNITION_QUERY = "cognition.query"
    COGNITION_QUERY_RESPONSE = "cognition.query.response"
    COGNITION_THOUGHT = "cognition.thought"

    # ═══════════════════════════════════════════════════════════════════
    # MEMORY EVENTS
    # ═══════════════════════════════════════════════════════════════════
    MEMORY_STORE = "memory.store"
    MEMORY_RETRIEVE = "memory.retrieve"
    MEMORY_STORED = "memory.stored"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_QUERY = "memory.query"
    MEMORY_GET = "memory.get"
    MEMORY_UPDATE = "memory.update"
    MEMORY_DELETE = "memory.delete"
    MEMORY_FILTER = "memory.filter"
    MEMORY_ORGANIZE = "memory.organize"
    MEMORY_STRUCTURIZE = "memory.structurize"
    MEMORY_SKILLIZE = "memory.skillize"
    MEMORY_PARAMETERIZE = "memory.parameterize"
    MEMORY_EMBED = "memory.embed"
    MEMORY_LOAD = "memory.load"
    MEMORY_SAVE = "memory.save"
    MEMORY_RESULT = "memory.result"
    MEMORY_ERROR = "memory.error"
    MEMORY_FILTERED = "memory.filtered"
    MEMORY_ORGANIZED = "memory.organized"
    MEMORY_STRUCTURIZED = "memory.structurized"
    MEMORY_SKILLIZED = "memory.skillized"
    MEMORY_PARAMETERIZED = "memory.parameterized"

    # Raw memory events
    RAW_MEMORY_SESSION_START = "raw_memory.session.start"
    RAW_MEMORY_SESSION_END = "raw_memory.session.end"
    RAW_MEMORY_SESSION_CLOSED = "raw_memory.session.closed"
    RAW_MEMORY_UTTERANCE = "raw_memory.utterance"
    RAW_MEMORY_USER_UPDATE = "raw_memory.user.update"
    RAW_MEMORY_SUMMARY_REQUEST = "raw_memory.summary.request"
    RAW_MEMORY_ERROR = "raw_memory.error"
    RAW_MEMORY_RESULT = "raw_memory.result"
    SUMMARY_MEMORY_RESULT = "summary_memory.result"

    # ═══════════════════════════════════════════════════════════════════
    # EMOTION EVENTS
    # ═══════════════════════════════════════════════════════════════════
    EMOTION_QUERY = "emotion.query"
    EMOTION_REGULATE = "emotion.regulate"
    EMOTION_UPDATE = "emotion.update"
    EMOTION_CHANGED = "emotion.changed"
    EMOTION_ERROR = "emotion.error"

    # ═══════════════════════════════════════════════════════════════════
    # GOAL EVENTS
    # ═══════════════════════════════════════════════════════════════════
    GOAL_UPDATE = "goal.update"
    GOAL_QUERY = "goal.query"
    GOAL_UPDATED = "goal.updated"
    GOAL_CHANGED = "goal.changed"
    GOAL_ERROR = "goal.error"

    # ═══════════════════════════════════════════════════════════════════
    # WORLD MODEL EVENTS
    # ═══════════════════════════════════════════════════════════════════
    WORLD_UPDATED = "world.updated"
    WORLD_QUERY = "world.query"
    WORLD_QUERY_RESPONSE = "world.query.response"
    WORLD_OBSERVE = "world.observe"
    WORLD_CLEAR = "world.clear"

    # ═══════════════════════════════════════════════════════════════════
    # ACTION EVENTS
    # ═══════════════════════════════════════════════════════════════════
    ACTION_EXECUTE = "action.execute"
    ACTION_PLAN = "action.plan"
    ACTION_RESULT = "action.result"
    ACTION_COMPLETED = "action.completed"
    ACTION_FAILED = "action.failed"
    ACTION_PROGRESS = "action.progress"
    ACTION_ERROR = "action.error"

    # ═══════════════════════════════════════════════════════════════════
    # RESPONSE EVENTS (for UI routing)
    # ═══════════════════════════════════════════════════════════════════
    RESPONSE_GRADIO = "response.gradio"
    RESPONSE_REALTIME = "response.realtime"
    RESPONSE_TERMINAL = "response.terminal"

    # ═══════════════════════════════════════════════════════════════════
    # AGENT LIFECYCLE EVENTS
    # ═══════════════════════════════════════════════════════════════════
    AGENT_STOP = "agent.stop"

    # ═══════════════════════════════════════════════════════════════════
    # WILDCARD PATTERNS
    # ═══════════════════════════════════════════════════════════════════
    ALL_PERCEPTION = "perception.*"
    ALL_COGNITION = "cognition.*"
    ALL_MEMORY = "memory.*"
    ALL_ACTION = "action.*"
    ALL_EMOTION = "emotion.*"
    ALL_GOAL = "goal.*"
    ALL_WORLD = "world.*"
    ALL_RESPONSE = "response.*"
