# memory_cleaner.py

import logging
from datetime import datetime, timedelta, timezone
from typing import List

from aeiva.cognition.memory.memory_unit import MemoryUnit


class MemoryCleanerError(Exception):
    """Exception raised when an error occurs in the MemoryCleaner."""
    pass


# Alias map: callers can use either "by_time" or "time", etc.
_FILTER_ALIASES = {
    "by_time": "time",
    "by_modality": "modality",
    "by_type": "type",
    "by_tags": "tags",
    "by_status": "status",
}


class MemoryCleaner:
    """
    Filters memory units based on various criteria.

    Supported filter types (both short and ``by_*`` forms accepted):
        - time: Removes memory units older than a specified threshold.
        - modality: Keeps only memory units matching specified modalities.
        - type: Keeps only memory units matching specified types.
        - tags: Keeps only memory units matching any of the specified tags.
        - status: Keeps only memory units matching the specified status.
    """

    def filter(
        self,
        memory_units: List[MemoryUnit],
        filter_type: str,
        **kwargs
    ) -> List[MemoryUnit]:
        """
        Filter memory units by *filter_type*.

        Args:
            memory_units: Units to filter.
            filter_type: One of 'time'/'by_time', 'modality'/'by_modality',
                         'type'/'by_type', 'tags'/'by_tags', 'status'/'by_status'.
            **kwargs: Parameters for the chosen filter (see individual methods).

        Returns:
            Filtered list of MemoryUnits.

        Raises:
            MemoryCleanerError: On unknown filter_type or missing parameters.
        """
        canonical = _FILTER_ALIASES.get(filter_type, filter_type)

        try:
            if canonical == "time":
                threshold_days = kwargs.get("threshold_days")
                if threshold_days is None:
                    raise MemoryCleanerError("Missing 'threshold_days' parameter for time-based filtering.")
                return self._filter_time(memory_units, threshold_days)

            if canonical == "modality":
                modalities = kwargs.get("modalities")
                if not modalities:
                    raise MemoryCleanerError("Missing 'modalities' parameter for modality-based filtering.")
                return [u for u in memory_units if u.modality in modalities]

            if canonical == "type":
                types = kwargs.get("types")
                if not types:
                    raise MemoryCleanerError("Missing 'types' parameter for type-based filtering.")
                return [u for u in memory_units if u.type in types]

            if canonical == "tags":
                tags = set(kwargs.get("tags", []))
                if not tags:
                    raise MemoryCleanerError("Missing 'tags' parameter for tags-based filtering.")
                return [u for u in memory_units if tags.intersection(u.tags)]

            if canonical == "status":
                status = kwargs.get("status")
                if not status:
                    raise MemoryCleanerError("Missing 'status' parameter for status-based filtering.")
                return [u for u in memory_units if u.status == status]

            raise MemoryCleanerError(f"Unknown filter_type: {filter_type}")
        except MemoryCleanerError:
            raise
        except Exception as e:
            raise MemoryCleanerError(f"Failed to filter memory units: {e}")

    # Keep public aliases for backward compatibility
    def filter_by_time(self, memory_units: List[MemoryUnit], threshold_days: int) -> List[MemoryUnit]:
        return self._filter_time(memory_units, threshold_days)

    def filter_by_modality(self, memory_units: List[MemoryUnit], modalities: List[str]) -> List[MemoryUnit]:
        return [u for u in memory_units if u.modality in modalities]

    def filter_by_type(self, memory_units: List[MemoryUnit], types: List[str]) -> List[MemoryUnit]:
        return [u for u in memory_units if u.type in types]

    # --- internal ---

    def _filter_time(self, memory_units: List[MemoryUnit], threshold_days: int) -> List[MemoryUnit]:
        current_time = datetime.now(timezone.utc)
        threshold = timedelta(days=threshold_days)
        return [u for u in memory_units if (current_time - u.timestamp) <= threshold]
