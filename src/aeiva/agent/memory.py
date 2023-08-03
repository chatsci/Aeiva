from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Union, Optional, Tuple
from collections import deque


class Memory(ABC):
    """
    Abstract base class for the memory of an agent. This incorporates concepts from neuroscience and machine learning.
    """
    def __init__(self, short_term_capacity: int, long_term_capacity: int):
        self.short_term_memory = {}  # Working memory, storing temporary information
        self.long_term_memory = {}  # Long term memory, storing persisting information
        self.short_term_capacity = short_term_capacity
        self.long_term_capacity = long_term_capacity
        self.access_times = {}  # Keep track of access times for each memory item
        self.short_term_queue = deque(maxlen=short_term_capacity)  # Queue to keep track of addition order in short term memory
        self.long_term_queue = deque(maxlen=long_term_capacity)  # Queue to keep track of addition order in long term memory

    def remember(self, key: str, value: Any, term: str = "short"):
        if term == "short":
            self.short_term_queue.append(key)
            if len(self.short_term_memory) >= self.short_term_capacity:
                self.forget("short")
            self.short_term_memory[key] = value
        else:
            self.long_term_queue.append(key)
            if len(self.long_term_memory) >= self.long_term_capacity:
                self.forget("long")
            self.long_term_memory[key] = value
        self.access_times[key] = 0  # Initialize access times

    def retrieve(self, key: str, term: str = "short"):
        if term == "short":
            self.access_times[key] += 1  # Increase access times
            return self.short_term_memory.get(key)
        else:
            self.access_times[key] += 1  # Increase access times
            return self.long_term_memory.get(key)

    def forget(self, term: str = "short"):
        # Forget based on 'use-it-or-lose-it' principle
        if term == "short":
            oldest_item_key = self.short_term_queue.popleft()
            self.short_term_memory.pop(oldest_item_key)
            self.access_times.pop(oldest_item_key)
        else:
            oldest_item_key = self.long_term_queue.popleft()
            self.long_term_memory.pop(oldest_item_key)
            self.access_times.pop(oldest_item_key)

    @abstractmethod
    def decay(self):
        """
        Abstract method for decay function of memories over time. This should be implemented in a more specific subclass.
        """
        pass

    @abstractmethod
    def reinforce(self, key: str):
        """
        Abstract method for reinforcement function of memories over time. This should be implemented in a more specific subclass.
        """
        pass

    @abstractmethod
    def search_memory(self, query: Any) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Abstract method for searching both short and long term memories for the query and returns the found item. 
        This should be implemented in a more specific subclass using ML techniques.
        """
        pass

    @abstractmethod
    def self_organize(self):
        """
        Abstract method for self-organizing memory.
        This should be implemented in a more specific subclass.
        """
        pass
