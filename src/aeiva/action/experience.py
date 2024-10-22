from aeiva.action.procedure import Procedure
from aeiva.action.skill import Skill
from aeiva.action.action import Action
from typing import List, Dict, Any, Optional, Union


class Experience(Procedure):
    """
    Represents an experience, which is a structured composition of actions.
    Unlike a skill, an experience cannot be executed until it is validated and transformed into a skill.
    
    Attributes:
        owner (str): The person or agent who owns the experience.
        reliable (bool): A flag indicating whether the experience is reliable enough to be transformed into a skill.
    """

    def __init__(self, name: str, steps: List[Union['Experience', Action]],
                 owner: Optional[str] = None, reliable: Optional[bool] = False,
                 id: Optional[str] = None, dependent_ids: Optional[List[str]] = None,
                 type: Optional[str] = None, description: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initializes a Skill by extending Procedure.
        """
        super().__init__(name=name, steps=steps,
                         id=id, dependent_ids=dependent_ids,
                         type=type, description=description,
                         metadata=metadata)
        self.type = "Experience"
        self.owner = owner  # The owner of the experience
        self.reliable = reliable  # Whether the experience can be transformed into a skill. 
                                  # We can use metadata to store some scored and decide whether it is reliable.

    @property
    def is_reliable(self) -> bool:
        """
        Checks if the experience is reliable enough to be transformed into a skill.
        """
        return self.reliable

    def mark_reliable(self) -> None:
        """
        Marks the experience as reliable, allowing it to be transformed into a skill.
        """
        self.reliable = True
    
    def to_skill(self) -> Skill:
        """
        Converts this experience into a skill, but only if the experience is marked as reliable.
        If the experience is not reliable, raises a ValueError.
        
        Returns:
            Skill: A new Skill object that is based on the actions from this experience.
        """
        if not self.reliable:
            raise ValueError(f"Experience {self.id} cannot be transformed into a skill because it is not marked as reliable.")
        
        # Create and return a new Skill instance
        return Skill(
            name=self.name,
            steps=self.steps,  # Use the same steps (actions) from the experience
            id=self.id,
            dependent_ids=self.dependent_ids,
            type="Skill",
            description=f"Skill derived from Experience: {self.description}", 
            metadata=self.metadata
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Returns a dictionary representation of the object.
        """
        experience_dict = super().to_dict()
        experience_dict.update({
            "owner": self.owner,
            "reliable": self.reliable,
        })
        return experience_dict