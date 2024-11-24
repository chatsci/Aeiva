# memory_organizer.py

import logging
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime, timezone

from aeiva.cognition.memory.memory_unit import MemoryUnit
from aeiva.cognition.memory.memory_link import MemoryLink


class MemoryOrganizerError(Exception):
    """Exception raised when an error occurs in the MemoryOrganizer."""
    pass


class MemoryOrganizer:
    """
    A class to organize memory units based on various organizing algorithms.

    Supported organize types:
        - 'dialogue': Groups memory units by 'dialogue_session_id'.
        # Future organize types can be added here.
    """

    def __init__(self):
        """
        Initializes the MemoryOrganizer.

        Currently, no initialization parameters are required.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Initialized MemoryOrganizer without default parameters.")

    def organize(
        self,
        memory_units: List[MemoryUnit],
        organize_type: str,
        **kwargs
    ) -> List[MemoryUnit]:
        """
        Organizes the provided memory units based on the specified organize type.

        Args:
            memory_units (List[MemoryUnit]): The list of memory units to be organized.
            organize_type (str): The type of organizing algorithm to use ('dialogue').
            **kwargs: Additional parameters required for specific organizers.
                For 'dialogue' organize:
                    - group_field (str): The metadata field to group by (default: 'dialogue_session_id').
                    - derive_content (bool): Whether to derive content for the group (default: True).
                    - derivation_type (str): The type of derivation to perform ('summary', etc.).

        Returns:
            List[MemoryUnit]: The list of memory units after organizing.

        Raises:
            MemoryOrganizerError: If an unknown organize_type is provided or if required parameters are missing.
        """
        self.logger.debug(f"Organizing memory units using organize_type='{organize_type}' with kwargs={kwargs}")
        try:
            if organize_type == 'dialogue':
                group_field = kwargs.get('group_field', 'dialogue_session_id')
                derive_content = kwargs.get('derive_content', True)
                derivation_type = kwargs.get('derivation_type', 'summary')
                return self.organize_by_dialogue(memory_units, group_field, derive_content, derivation_type)
            else:
                self.logger.error(f"Unknown organize_type: {organize_type}")
                raise MemoryOrganizerError(f"Unknown organize_type: {organize_type}")
        except MemoryOrganizerError:
            # Re-raise custom errors without modification
            raise
        except Exception as e:
            self.logger.error(f"Failed to organize memory units: {e}")
            raise MemoryOrganizerError(f"Failed to organize memory units: {e}")

    def organize_by_dialogue(
        self,
        memory_units: List[MemoryUnit],
        group_field: str = 'dialogue_session_id',  # NOTE: here we assume the meta data field of dialogue memory units has a dialogue_session_id
        derive_content: bool = False,
        derivation_type: str = 'summary'
    ) -> List[MemoryUnit]:
        """
        Organizes memory units into dialogue sessions based on a common 'dialogue_session_id'.

        Args:
            memory_units (List[MemoryUnit]): The list of memory units to be organized.
            group_field (str): The metadata field to group by (default: 'dialogue_session_id').
            derive_content (bool): Whether to derive content for the group (default: True).
            derivation_type (str): The type of derivation to perform ('summary', etc.).

        Returns:
            List[MemoryUnit]: The list of memory units after organizing, including new dialogue groups.

        Raises:
            MemoryOrganizerError: If organizing fails.
        """
        self.logger.debug(f"Organizing by dialogue with group_field='{group_field}', derive_content={derive_content}, derivation_type='{derivation_type}'")
        try:
            # Group memory units by the specified group_field
            groups = defaultdict(list)
            for mu in memory_units:
                group_id = mu.metadata.get(group_field)
                if group_id:
                    groups[group_id].append(mu)
                else:
                    self.logger.debug(f"MemoryUnit '{mu.id}' does not have '{group_field}'. Skipping grouping.")

            self.logger.info(f"Found {len(groups)} dialogue groups based on '{group_field}'.")

            # Create new MemoryUnit for each group
            new_memory_units = []
            for group_id, group_mus in groups.items():
                self.logger.debug(f"Creating DialogueGroup for group_id='{group_id}' with {len(group_mus)} memory units.")

                # Create a new MemoryUnit to represent the DialogueGroup
                dialogue_group = MemoryUnit(
                    content="",  # Content to be derived
                    type="dialogue_session",
                    metadata={
                        "organized_at": datetime.now(timezone.utc).isoformat(),
                        "member_ids": [mu.id for mu in group_mus],
                        "derivation_type": derivation_type
                    }
                )

                # Link each memory unit to the DialogueGroup
                for mu in group_mus:
                    link = MemoryLink(
                        source_id=mu.id,
                        target_id=dialogue_group.id,
                        relationship='part_of'
                    )
                    mu.edges.append(link)
                    self.logger.debug(f"Linked MemoryUnit '{mu.id}' to DialogueGroup '{dialogue_group.id}'.")

                # Optionally, derive content for the group
                if derive_content:
                    if derivation_type == 'summary':
                        derived_content = self.derive_summary(group_mus)
                    elif derivation_type == 'reflection':
                        derived_content = self.derive_reflection(group_mus)
                    else:
                        self.logger.warning(f"Unknown derivation_type '{derivation_type}'. Skipping content derivation.")
                        derived_content = ""
                    dialogue_group.content = derived_content
                    dialogue_group.status = 'derived'
                    self.logger.debug(f"Derived content for DialogueGroup '{dialogue_group.id}': {derived_content}")

                new_memory_units.append(dialogue_group)
                self.logger.info(f"DialogueGroup '{dialogue_group.id}' created for group_id='{group_id}'.")

            # Return the original memory units plus the new dialogue groups
            organized_memory = memory_units + new_memory_units
            self.logger.debug(f"Organizing by dialogue completed. Total memory units after organizing: {len(organized_memory)}")
            return organized_memory

        except Exception as e:
            self.logger.error(f"Error organizing by dialogue: {e}")
            raise MemoryOrganizerError(f"Error organizing by dialogue: {e}")

    def derive_summary(self, memory_units: List[MemoryUnit]) -> str: # TODO: replace with lmp implementation
        """
        Derives a summary from the given memory units.

        Args:
            memory_units (List[MemoryUnit]): The list of memory units to summarize.

        Returns:
            str: A summary string.
        """
        self.logger.debug(f"Deriving summary from {len(memory_units)} memory units.")
        try:
            summary = "Summary of dialogue session:\n"
            for mu in memory_units:
                summary += f"- {mu.content}\n"
            derived_summary = summary.strip()
            self.logger.debug(f"Derived summary: {derived_summary}")
            return derived_summary
        except Exception as e:
            self.logger.error(f"Failed to derive summary: {e}")
            raise MemoryOrganizerError(f"Failed to derive summary: {e}")

    def derive_reflection(self, memory_units: List[MemoryUnit]) -> str: # TODO: replace with lmp implementation
        """
        Derives a reflection from the given memory units.

        Args:
            memory_units (List[MemoryUnit]): The list of memory units to reflect upon.

        Returns:
            str: A reflection string.
        """
        self.logger.debug(f"Deriving reflection from {len(memory_units)} memory units.")
        try:
            reflection = "Reflection on dialogue session:\n"
            for mu in memory_units:
                reflection += f"- {mu.content}\n"
            derived_reflection = reflection.strip()
            self.logger.debug(f"Derived reflection: {derived_reflection}")
            return derived_reflection
        except Exception as e:
            self.logger.error(f"Failed to derive reflection: {e}")
            raise MemoryOrganizerError(f"Failed to derive reflection: {e}")