# test2.py

import logging
from typing import List
from datetime import datetime, timedelta, timezone

# Import the MemoryStructurer and MemoryUnit from memory_structurer.py and memory_unit.py
from memory_structurer import MemoryStructurer, MemoryStructurerError
from aeiva.cognition.memory.memory_unit import MemoryUnit

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    # Initialize MemoryStructurer
    structurer = MemoryStructurer()

    # Create sample memory units
    memory_units: List[MemoryUnit] = [
        MemoryUnit(
            id="mu1",
            content="Sample content 1",
            timestamp=datetime.now(timezone.utc) - timedelta(days=1),
            modality="text",
            type="sample_type",
            priority=5,
            metadata={
                "structuring_session_id": "struct_session_1"
            }
        ),
        MemoryUnit(
            id="mu2",
            content="Sample content 2",
            timestamp=datetime.now(timezone.utc) - timedelta(days=2),
            modality="image",
            type="sample_type",
            priority=3,
            metadata={
                "structuring_session_id": "struct_session_1"
            }
        ),
        MemoryUnit(
            id="mu3",
            content="Sample content 3",
            timestamp=datetime.now(timezone.utc) - timedelta(days=3),
            modality="audio",
            type="sample_type",
            priority=2,
            metadata={
                "structuring_session_id": "struct_session_2"
            }
        ),
    ]

    # Apply structuring with example structuring type
    try:
        structured_memory = structurer.structure(
            memory_units=memory_units,
            structure_type='structure_type_example',
            additional_param='value'  # Example of additional parameters
        )
        print("Structured Memory Units:")
        for mu in structured_memory:
            print(mu.to_dict())
    except MemoryStructurerError as e:
        print(f"Structuring error: {e}")

    # Attempt to use an unsupported structure_type
    try:
        structurer.structure(
            memory_units=memory_units,
            structure_type='unknown_structure_type'
        )
    except MemoryStructurerError as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    main()