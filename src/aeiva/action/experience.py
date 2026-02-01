"""
Experience: A personalized composition of Actions awaiting validation.

An Experience is like a Skill but represents learned behavior that
hasn't been validated yet. Once validated, it can be transformed
into a Skill for execution.

Use Cases:
    - Recording user interactions for learning
    - Capturing workflows that might become reusable
    - Storing personalized procedures before standardization

Hierarchy:
    Procedure → Plan (composed of Tasks, visualizable)
    Procedure → Skill (composed of Actions, executable)
    Procedure → Experience (composed of Actions, needs validation)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from aeiva.action.procedure import Procedure, generate_procedure_id
from aeiva.action.action import Action
from aeiva.action.skill import Skill


@dataclass
class Experience(Procedure):
    """
    A personalized composition of Actions awaiting validation.

    Experiences capture learned behaviors or workflows that haven't
    been validated for general use. They have an owner and must be
    marked as reliable before being converted to Skills.

    Validation Flow:
        1. Experience is created with actions
        2. Experience is tested/evaluated
        3. Experience is marked reliable
        4. Experience is converted to Skill

    Attributes:
        owner: Identifier of who owns this experience
        reliable: Whether this experience is validated
        recorded_at: When the experience was captured
        validation_score: Optional score from validation process

    Example:
        # Record an experience
        experience = Experience(
            name="user_workflow",
            steps=[action1, action2],
            owner="user_123",
            description="User's preferred way to process data"
        )

        # After validation
        experience.validate(score=0.95)

        # Convert to reusable skill
        if experience.is_reliable:
            skill = experience.to_skill()
            await skill.execute()
    """

    steps: List[Union["Experience", Action]] = field(default_factory=list)
    owner: str = field(default="")
    reliable: bool = field(default=False)
    recorded_at: datetime = field(default_factory=datetime.now)
    validation_score: Optional[float] = field(default=None)

    @property
    def is_reliable(self) -> bool:
        """Check if the experience has been validated as reliable."""
        return self.reliable

    def validate(self, score: Optional[float] = None, threshold: float = 0.8) -> bool:
        """
        Validate the experience with an optional score.

        Args:
            score: Validation score (0.0 to 1.0)
            threshold: Minimum score to be considered reliable

        Returns:
            True if experience is now marked reliable
        """
        self.validation_score = score

        if score is not None:
            self.reliable = score >= threshold
        else:
            self.reliable = True

        return self.reliable

    def mark_reliable(self) -> None:
        """Manually mark the experience as reliable."""
        self.reliable = True

    def mark_unreliable(self) -> None:
        """Mark the experience as unreliable."""
        self.reliable = False

    def to_skill(self) -> Skill:
        """
        Convert this experience into an executable Skill.

        Returns:
            New Skill based on this experience's actions

        Raises:
            ValueError: If experience is not marked as reliable
        """
        if not self.reliable:
            raise ValueError(
                f"Experience '{self.id}' cannot be converted to skill: "
                f"not marked as reliable (validation_score={self.validation_score})"
            )

        return Skill(
            name=self.name,
            steps=self.steps.copy(),  # Copy to avoid shared state
            id=f"skill_from_{self.id}",
            dependent_ids=self.dependent_ids.copy(),
            description=f"Skill derived from experience: {self.description}",
            metadata={
                **self.metadata,
                "source_experience": self.id,
                "source_owner": self.owner,
                "validation_score": self.validation_score,
            },
        )

    def add_action(self, action: Action) -> "Experience":
        """
        Add an action to the experience.

        Args:
            action: Action to add

        Returns:
            Self for chaining
        """
        existing_ids = {step.id for step in self.steps}
        for dep_id in action.dependent_ids:
            if dep_id not in existing_ids:
                raise ValueError(
                    f"Action '{action.id}' depends on '{dep_id}' "
                    f"which is not in the experience"
                )

        self.steps.append(action)
        self._build_graph()
        return self

    @property
    def actions(self) -> List[Action]:
        """Get all actions (excluding nested experiences)."""
        return [step for step in self.steps if isinstance(step, Action)]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = super().to_dict()
        data.update({
            "owner": self.owner,
            "reliable": self.reliable,
            "recorded_at": self.recorded_at.isoformat(),
            "validation_score": self.validation_score,
        })
        return data

    def __str__(self) -> str:
        reliability = "reliable" if self.reliable else "unvalidated"
        return f"Experience({self.name}, owner={self.owner}, {reliability})"
