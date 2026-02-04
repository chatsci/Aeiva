"""
Response Classifier: Determines the type of LLM response.

This module provides clean classification of LLM responses into:
- TEXT: Plain natural language (stream to user)
- JSON: Action envelope (parse and execute)
- MIXED: Both text and JSON present

The classifier uses structural analysis rather than heuristics.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple


class ResponseType(Enum):
    """Classification of LLM response content."""
    UNDETERMINED = auto()  # Not enough content to classify
    TEXT = auto()          # Plain natural language
    JSON = auto()          # Pure JSON (action envelope)
    MIXED = auto()         # Text before/after JSON


@dataclass
class ClassificationResult:
    """Result of response classification."""
    response_type: ResponseType
    confidence: float  # 0.0 to 1.0
    json_start: Optional[int] = None  # Character index where JSON starts
    json_end: Optional[int] = None    # Character index where JSON ends
    text_before: str = ""             # Text content before JSON
    text_after: str = ""              # Text content after JSON
    json_blocks: List[str] = None     # Extracted JSON blocks

    def __post_init__(self):
        if self.json_blocks is None:
            self.json_blocks = []


class ResponseClassifier:
    """
    Classifies LLM responses by structural analysis.

    Design principles:
    - No heuristics that can fail silently
    - Clear confidence levels
    - Handles edge cases explicitly
    """

    # Minimum characters before making a confident classification
    MIN_CLASSIFICATION_CHARS = 20

    # If we see this much text without JSON, it's definitely text
    TEXT_CONFIDENCE_THRESHOLD = 100

    @classmethod
    def classify(cls, content: str) -> ClassificationResult:
        """
        Classify response content.

        Args:
            content: The accumulated response content

        Returns:
            ClassificationResult with type and metadata
        """
        if not content:
            return ClassificationResult(
                response_type=ResponseType.UNDETERMINED,
                confidence=0.0,
            )

        stripped = content.strip()

        if len(stripped) < cls.MIN_CLASSIFICATION_CHARS:
            return cls._classify_short_content(stripped)

        return cls._classify_full_content(content)

    @classmethod
    def _classify_short_content(cls, content: str) -> ClassificationResult:
        """Classify content that's too short for confident classification."""
        stripped = content.strip()

        # If it starts with {, likely JSON - try to parse it
        if stripped.startswith("{"):
            # If it's complete valid JSON, classify it
            blocks, positions = cls._extract_all_json_blocks(stripped)
            if blocks:
                return ClassificationResult(
                    response_type=ResponseType.JSON,
                    confidence=0.9,
                    json_start=positions[0][0] if positions else None,
                    json_end=positions[-1][1] if positions else None,
                    json_blocks=blocks,
                )
            # Incomplete JSON - need more
            return ClassificationResult(
                response_type=ResponseType.UNDETERMINED,
                confidence=0.3,
            )

        # If it starts with text and doesn't contain {, it's likely plain text
        if stripped and stripped[0].isalpha() and "{" not in stripped:
            return ClassificationResult(
                response_type=ResponseType.TEXT,
                confidence=0.7,  # Moderate confidence for short text
                text_before=content,
            )

        # Contains { but doesn't start with it - might be mixed, need more
        if "{" in stripped:
            return ClassificationResult(
                response_type=ResponseType.UNDETERMINED,
                confidence=0.3,
            )

        return ClassificationResult(
            response_type=ResponseType.UNDETERMINED,
            confidence=0.0,
        )

    @classmethod
    def _classify_full_content(cls, content: str) -> ClassificationResult:
        """Classify content with enough characters for confident analysis."""
        # Extract all JSON blocks
        json_blocks, positions = cls._extract_all_json_blocks(content)

        if not json_blocks:
            # No JSON found - pure text
            return ClassificationResult(
                response_type=ResponseType.TEXT,
                confidence=1.0,
                text_before=content,
            )

        # Analyze structure
        first_start, first_end = positions[0]
        last_start, last_end = positions[-1]

        text_before = content[:first_start].strip()
        text_after = content[last_end:].strip()

        # Pure JSON: nothing significant before or after
        if not text_before and not text_after:
            return ClassificationResult(
                response_type=ResponseType.JSON,
                confidence=1.0,
                json_start=first_start,
                json_end=last_end,
                json_blocks=json_blocks,
            )

        # Mixed: has text and JSON
        return ClassificationResult(
            response_type=ResponseType.MIXED,
            confidence=0.9,
            json_start=first_start,
            json_end=last_end,
            text_before=text_before,
            text_after=text_after,
            json_blocks=json_blocks,
        )

    @classmethod
    def _extract_all_json_blocks(
        cls, content: str
    ) -> Tuple[List[str], List[Tuple[int, int]]]:
        """
        Extract ALL valid JSON objects from content.

        Returns:
            Tuple of (json_blocks, positions)
            - json_blocks: List of JSON strings
            - positions: List of (start, end) character indices
        """
        blocks: List[str] = []
        positions: List[Tuple[int, int]] = []

        # First try to extract from code fences
        fenced = list(re.finditer(
            r"```(?:json)?\s*(\{.*?\})\s*```",
            content,
            re.DOTALL
        ))
        if fenced:
            for match in fenced:
                json_str = match.group(1).strip()
                if cls._is_valid_json(json_str):
                    blocks.append(json_str)
                    positions.append((match.start(), match.end()))
            if blocks:
                return blocks, positions

        # Extract raw JSON objects
        decoder = json.JSONDecoder()
        idx = 0

        while idx < len(content):
            # Find next potential JSON start
            start = content.find("{", idx)
            if start == -1:
                break

            try:
                obj, end_offset = decoder.raw_decode(content[start:])
                end = start + end_offset

                # Validate it's an object (not just valid JSON syntax)
                if isinstance(obj, dict):
                    blocks.append(content[start:end])
                    positions.append((start, end))

                idx = end
            except json.JSONDecodeError:
                idx = start + 1

        return blocks, positions

    @staticmethod
    def _is_valid_json(text: str) -> bool:
        """Check if text is valid JSON."""
        try:
            result = json.loads(text)
            return isinstance(result, dict)
        except (json.JSONDecodeError, TypeError):
            return False

    @classmethod
    def is_confident(cls, result: ClassificationResult) -> bool:
        """Check if classification is confident enough to act on."""
        if result.response_type == ResponseType.UNDETERMINED:
            return False
        return result.confidence >= 0.7

    @classmethod
    def should_buffer_more(
        cls,
        result: ClassificationResult,
        content_length: int,
        max_buffer: int = 500,
    ) -> bool:
        """
        Determine if we should buffer more content before acting.

        Args:
            result: Current classification result
            content_length: Current content length
            max_buffer: Maximum chars to buffer before forcing a decision

        Returns:
            True if more buffering is recommended
        """
        # If we've hit max buffer, stop buffering
        if content_length >= max_buffer:
            return False

        # If classification is confident, no need to buffer
        if cls.is_confident(result):
            return False

        # If undetermined, keep buffering
        if result.response_type == ResponseType.UNDETERMINED:
            return True

        return False
