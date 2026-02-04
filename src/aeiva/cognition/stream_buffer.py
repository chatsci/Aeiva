"""
Stream Buffer: Manages buffering of streaming responses.

This module provides intelligent buffering that:
- Collects chunks until classification is possible
- Decides when to flush content to the user
- Handles the streaming/classification tension cleanly
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Callable, Awaitable

from aeiva.cognition.response_classifier import (
    ResponseClassifier,
    ClassificationResult,
    ResponseType,
)


@dataclass
class FlushDecision:
    """Decision about what to flush from the buffer."""
    should_flush: bool
    content: str = ""
    is_final: bool = False
    classification: Optional[ClassificationResult] = None


@dataclass
class StreamBuffer:
    """
    Intelligent buffer for streaming LLM responses.

    The buffer collects chunks and makes smart decisions about when
    to release content to the user vs when to hold for classification.

    Design principles:
    - Clear state transitions
    - Predictable behavior
    - No content loss
    """

    # Configuration
    min_classification_chars: int = 50
    max_buffer_chars: int = 500
    stream_text_immediately: bool = True

    # State
    chunks: List[str] = field(default_factory=list)
    classification: ClassificationResult = field(
        default_factory=lambda: ClassificationResult(
            response_type=ResponseType.UNDETERMINED,
            confidence=0.0,
        )
    )
    flushed_count: int = 0  # Characters already flushed
    is_finalized: bool = False
    _decision_made: bool = False

    @property
    def content(self) -> str:
        """Get all buffered content."""
        return "".join(self.chunks)

    @property
    def unflushed_content(self) -> str:
        """Get content that hasn't been flushed yet."""
        full = self.content
        return full[self.flushed_count:]

    @property
    def content_length(self) -> int:
        """Total content length."""
        return sum(len(c) for c in self.chunks)

    def add_chunk(self, chunk: str) -> FlushDecision:
        """
        Add a chunk to the buffer.

        Args:
            chunk: New content chunk

        Returns:
            FlushDecision indicating what (if anything) should be flushed
        """
        if self.is_finalized:
            raise RuntimeError("Cannot add to finalized buffer")

        self.chunks.append(chunk)

        # Reclassify with new content
        self.classification = ResponseClassifier.classify(self.content)

        return self._make_flush_decision()

    def _make_flush_decision(self) -> FlushDecision:
        """Determine what to flush based on current state."""
        content_len = self.content_length

        # If we haven't reached minimum, don't flush yet
        if content_len < self.min_classification_chars:
            return FlushDecision(should_flush=False)

        # If content starts with {, always buffer (likely JSON)
        stripped = self.content.lstrip()
        if stripped.startswith("{"):
            # Don't flush JSON-looking content
            return FlushDecision(should_flush=False, classification=self.classification)

        # Check if we should buffer more
        if ResponseClassifier.should_buffer_more(
            self.classification,
            content_len,
            self.max_buffer_chars,
        ):
            return FlushDecision(should_flush=False)

        # Decision point reached
        self._decision_made = True

        # Handle based on classification
        if self.classification.response_type == ResponseType.TEXT:
            # Pure text - flush everything unflushed
            to_flush = self.unflushed_content
            if to_flush:
                self.flushed_count = self.content_length
                return FlushDecision(
                    should_flush=True,
                    content=to_flush,
                    classification=self.classification,
                )

        elif self.classification.response_type == ResponseType.JSON:
            # Pure JSON - don't flush, will be processed as action
            return FlushDecision(
                should_flush=False,
                classification=self.classification,
            )

        elif self.classification.response_type == ResponseType.MIXED:
            # Mixed - flush text_before if not already flushed
            text_before = self.classification.text_before
            if text_before and self.flushed_count < len(text_before):
                to_flush = text_before[self.flushed_count:]
                self.flushed_count = len(text_before)
                return FlushDecision(
                    should_flush=True,
                    content=to_flush,
                    classification=self.classification,
                )

        return FlushDecision(should_flush=False, classification=self.classification)

    def finalize(self) -> FlushDecision:
        """
        Finalize the buffer - no more chunks coming.

        Returns:
            Final flush decision
        """
        self.is_finalized = True

        # Final classification
        self.classification = ResponseClassifier.classify(self.content)

        # For pure JSON, never flush (will be processed as actions)
        if self.classification.response_type == ResponseType.JSON:
            return FlushDecision(
                should_flush=False,
                is_final=True,
                classification=self.classification,
            )

        # For pure text, flush any remaining
        if self.classification.response_type == ResponseType.TEXT:
            to_flush = self.unflushed_content
            if to_flush:
                self.flushed_count = self.content_length
                return FlushDecision(
                    should_flush=True,
                    content=to_flush,
                    is_final=True,
                    classification=self.classification,
                )

        # For mixed, flush text_after if present (text_before should already be flushed)
        if self.classification.response_type == ResponseType.MIXED:
            text_after = self.classification.text_after
            if text_after:
                return FlushDecision(
                    should_flush=True,
                    content=text_after,
                    is_final=True,
                    classification=self.classification,
                )

        # For UNDETERMINED with no JSON, treat as text
        if (
            self.classification.response_type == ResponseType.UNDETERMINED
            and not self.classification.json_blocks
        ):
            to_flush = self.unflushed_content
            if to_flush:
                self.flushed_count = self.content_length
                return FlushDecision(
                    should_flush=True,
                    content=to_flush,
                    is_final=True,
                    classification=self.classification,
                )

        return FlushDecision(
            should_flush=False,
            is_final=True,
            classification=self.classification,
        )

    def get_json_content(self) -> List[str]:
        """Get extracted JSON blocks (if any)."""
        return self.classification.json_blocks or []

    def get_display_text(self) -> str:
        """
        Get text that should be displayed to the user.

        For TEXT: all content
        For JSON: nothing (actions only)
        For MIXED: text_before + text_after
        """
        if self.classification.response_type == ResponseType.TEXT:
            return self.content

        if self.classification.response_type == ResponseType.JSON:
            return ""

        if self.classification.response_type == ResponseType.MIXED:
            parts = []
            if self.classification.text_before:
                parts.append(self.classification.text_before)
            if self.classification.text_after:
                parts.append(self.classification.text_after)
            return " ".join(parts)

        return self.content

    def reset(self) -> None:
        """Reset buffer state for reuse."""
        self.chunks.clear()
        self.classification = ClassificationResult(
            response_type=ResponseType.UNDETERMINED,
            confidence=0.0,
        )
        self.flushed_count = 0
        self.is_finalized = False
        self._decision_made = False
