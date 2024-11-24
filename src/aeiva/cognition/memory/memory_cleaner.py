# memory_cleaner.py

import logging
from datetime import datetime, timedelta, UTC
from typing import List, Dict, Any, Optional

from aeiva.cognition.memory.memory_unit import MemoryUnit
from aeiva.cognition.memory.memory_link import MemoryLink


class MemoryCleanerError(Exception):
    """Exception raised when an error occurs in the MemoryCleaner."""
    pass


class MemoryCleaner:
    """
    A class to clean memory units based on various filtering algorithms.

    Supported filter types:
        - 'time': Removes memory units older than a specified threshold.
        - 'modality': Keeps only memory units matching specified modalities.
        - 'type': Keeps only memory units matching specified types.
    """

    def __init__(self):
        """
        Initializes the MemoryCleaner.

        Currently, no initialization parameters are required.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Initialized MemoryCleaner without default parameters.")

    def filter(
        self,
        memory_units: List[MemoryUnit],
        filter_type: str,
        **kwargs
    ) -> List[MemoryUnit]:
        """
        Filters the provided memory units based on the specified filter type.

        Args:
            memory_units (List[MemoryUnit]): The list of memory units to be filtered.
            filter_type (str): The type of filtering algorithm to use ('time', 'modality', 'type').
            **kwargs: Additional parameters required for specific filters.
                For 'time' filter:
                    - threshold_days (int): Number of days beyond which memory units are removed.
                For 'modality' filter:
                    - modalities (List[str]): List of modalities to retain (e.g., ['text', 'image']).
                For 'type' filter:
                    - types (List[str]): List of types to retain (e.g., ['dialogue', 'summary']).

        Returns:
            List[MemoryUnit]: The list of memory units after filtering.

        Raises:
            MemoryCleanerError: If an unknown filter_type is provided or if required parameters are missing.
        """
        self.logger.debug(f"Filtering memory units using filter_type='{filter_type}' with kwargs={kwargs}")
        try:
            if filter_type == 'time':
                threshold_days = kwargs.get('threshold_days')
                if threshold_days is None:
                    self.logger.error("Missing 'threshold_days' parameter for time-based filtering.")
                    raise MemoryCleanerError("Missing 'threshold_days' parameter for time-based filtering.")
                return self.filter_by_time(memory_units, threshold_days)
            elif filter_type == 'modality':
                modalities = kwargs.get('modalities')
                if not modalities:
                    self.logger.error("Missing 'modalities' parameter for modality-based filtering.")
                    raise MemoryCleanerError("Missing 'modalities' parameter for modality-based filtering.")
                return self.filter_by_modality(memory_units, modalities)
            elif filter_type == 'type':
                types = kwargs.get('types')
                if not types:
                    self.logger.error("Missing 'types' parameter for type-based filtering.")
                    raise MemoryCleanerError("Missing 'types' parameter for type-based filtering.")
                return self.filter_by_type(memory_units, types)
            else:
                self.logger.error(f"Unknown filter_type: {filter_type}")
                raise MemoryCleanerError(f"Unknown filter_type: {filter_type}")
        except MemoryCleanerError:
            # Re-raise custom errors without modification
            raise
        except Exception as e:
            self.logger.error(f"Failed to filter memory units: {e}")
            raise MemoryCleanerError(f"Failed to filter memory units: {e}")
    # TODO: more filter options

    def filter_by_time(self, memory_units: List[MemoryUnit], threshold_days: int) -> List[MemoryUnit]:
        """
        Removes memory units older than the specified threshold_days.

        Args:
            memory_units (List[MemoryUnit]): The list of memory units to be filtered.
            threshold_days (int): Number of days beyond which memory units are removed.

        Returns:
            List[MemoryUnit]: The list of memory units after time-based filtering.

        Raises:
            MemoryCleanerError: If filtering fails.
        """
        self.logger.debug(f"Applying time-based filtering with threshold_days={threshold_days}")
        try:
            current_time = datetime.now(UTC)
            threshold = timedelta(days=threshold_days)
            filtered_memory = [
                mu for mu in memory_units
                if (current_time - mu.timestamp) <= threshold
            ]
            removed_count = len(memory_units) - len(filtered_memory)
            self.logger.info(
                f"Time-based filter: Removed {removed_count} memory units older than {threshold_days} days."
            )
            return filtered_memory
        except Exception as e:
            self.logger.error(f"Time-based filtering failed: {e}")
            raise MemoryCleanerError(f"Time-based filtering failed: {e}")

    def filter_by_modality(self, memory_units: List[MemoryUnit], modalities: List[str]) -> List[MemoryUnit]:
        """
        Keeps only memory units that match the specified modalities.

        Args:
            memory_units (List[MemoryUnit]): The list of memory units to be filtered.
            modalities (List[str]): List of modalities to retain (e.g., ['text', 'image']).

        Returns:
            List[MemoryUnit]: The list of memory units after modality-based filtering.

        Raises:
            MemoryCleanerError: If filtering fails.
        """
        self.logger.debug(f"Applying modality-based filtering with modalities={modalities}")
        try:
            if not modalities:
                self.logger.warning("No modalities specified for modality-based filtering. Returning original memory units.")
                return memory_units

            filtered_memory = [
                mu for mu in memory_units
                if mu.modality in modalities
            ]
            removed_count = len(memory_units) - len(filtered_memory)
            self.logger.info(
                f"Modality-based filter: Removed {removed_count} memory units not in modalities {modalities}."
            )
            return filtered_memory
        except Exception as e:
            self.logger.error(f"Modality-based filtering failed: {e}")
            raise MemoryCleanerError(f"Modality-based filtering failed: {e}")

    def filter_by_type(self, memory_units: List[MemoryUnit], types: List[str]) -> List[MemoryUnit]:
        """
        Keeps only memory units that match the specified types.

        Args:
            memory_units (List[MemoryUnit]): The list of memory units to be filtered.
            types (List[str]): List of types to retain (e.g., ['dialogue', 'summary']).

        Returns:
            List[MemoryUnit]: The list of memory units after type-based filtering.

        Raises:
            MemoryCleanerError: If filtering fails.
        """
        self.logger.debug(f"Applying type-based filtering with types={types}")
        try:
            if not types:
                self.logger.warning("No types specified for type-based filtering. Returning original memory units.")
                return memory_units

            filtered_memory = [
                mu for mu in memory_units
                if mu.type in types
            ]
            removed_count = len(memory_units) - len(filtered_memory)
            self.logger.info(
                f"Type-based filter: Removed {removed_count} memory units not in types {types}."
            )
            return filtered_memory
        except Exception as e:
            self.logger.error(f"Type-based filtering failed: {e}")
            raise MemoryCleanerError(f"Type-based filtering failed: {e}")
    
    # TODO: more filter methods