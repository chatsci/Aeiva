# File: cognition/emotion_category.py

from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class CategoryEmotionState:
    """
    Represents the emotional state in a Category-Based Model with extensive categories.
    
    Attributes:
        emotion_label (str): The current emotion category.
        intensity (float): The intensity of the current emotion (range: 0.0 to 1.0).
    """
    emotion_label: str = "neutral"
    intensity: float = 0.0  # Optional: Represents the strength of the emotion

    def to_dict(self) -> Dict[str, Any]:
        return {
            'emotion_label': self.emotion_label,
            'intensity': self.intensity
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        return CategoryEmotionState(
            emotion_label=data.get('emotion_label', 'neutral'),
            intensity=data.get('intensity', 0.0)
        )

# File: cognition/emotion_category.py

from typing import Dict, Any, Set
from aeiva.cognition.emotion.emotion import Emotion, ConfigurationError, UpdateError, RegulationError
import asyncio
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CategoryEmotion(Emotion[CategoryEmotionState]):
    """
    Concrete implementation of the Emotion base class using an extensive Category-Based Model.
    """
    
    # Define the extensive set of emotion categories
    EMOTION_CATEGORIES: Set[str] = {
        # Positive Emotions
        'admiration', 'amusement', 'approval', 'caring', 'desire', 'excitement',
        'gratitude', 'joy', 'love', 'optimism', 'pride', 'relief',
        # Negative Emotions
        'anger', 'annoyance', 'disappointment', 'disapproval', 'disgust',
        'embarrassment', 'fear', 'grief', 'nervousness', 'remorse', 'sadness',
        # Ambiguous Emotions
        'confusion', 'curiosity', 'realization', 'surprise', 'awe',
        # Additional Emotions
        'frustration', 'hope', 'guilt', 'contentment', 'boredom',
        'loneliness', 'elation'
    }
    
    def init_state(self) -> CategoryEmotionState:
        """
        Initialize the emotional state with a default emotion.
        
        Returns:
            CategoryEmotionState: Initialized state with 'neutral' emotion.
        """
        default_emotion = self.config.get('default_emotion', 'neutral')
        default_intensity = self.config.get('default_intensity', 0.0)
        if default_emotion not in self.EMOTION_CATEGORIES and default_emotion != 'neutral':
            raise ConfigurationError(f"Invalid default emotion: {default_emotion}")
        return CategoryEmotionState(emotion_label=default_emotion, intensity=default_intensity)
    
    async def setup(self) -> None:
        """
        Set up the Category Emotion system.
        
        Raises:
            ConfigurationError: If required configuration parameters are missing or invalid.
        """
        required_keys = ['allowed_emotions', 'regulation_strategies']
        for key in required_keys:
            if key not in self.config:
                raise ConfigurationError(f"Missing configuration parameter: {key}")
        
        # Initialize allowed emotions
        self.allowed_emotions = set(self.config['allowed_emotions'])
        if not self.allowed_emotions.issubset(self.EMOTION_CATEGORIES):
            invalid_emotions = self.allowed_emotions - self.EMOTION_CATEGORIES
            raise ConfigurationError(f"Invalid emotions in allowed_emotions: {invalid_emotions}")
        
        # Initialize regulation strategies
        self.regulation_strategies = set(self.config['regulation_strategies'])
        valid_strategies = {'neutralize', 'increase', 'decrease', 'toggle'}
        if not self.regulation_strategies.issubset(valid_strategies):
            invalid_strategies = self.regulation_strategies - valid_strategies
            raise ConfigurationError(f"Invalid regulation strategies: {invalid_strategies}")
        
        logging.info("CategoryEmotion setup complete.")
    
    async def update(self, input_data: Dict[str, Any]) -> None:
        """
        Update the emotional state based on input stimuli.
        
        Args:
            input_data (Dict[str, Any]): Stimuli data affecting emotion.
                Expected key: 'emotion_label' (str), 'intensity' (float, optional)
        
        Raises:
            UpdateError: If updating the emotional state fails.
        """
        try:
            new_emotion = input_data.get('emotion_label')
            if not new_emotion:
                raise ValueError("Missing 'emotion_label' in input_data.")
            if new_emotion not in self.allowed_emotions:
                raise ValueError(f"Emotion '{new_emotion}' is not allowed in this model.")
            
            new_intensity = input_data.get('intensity', 1.0)  # Default intensity
            
            if not (0.0 <= new_intensity <= 1.0):
                raise ValueError("Intensity must be between 0.0 and 1.0.")
            
            # Update the state
            self.state.emotion_label = new_emotion
            self.state.intensity = new_intensity
            
            logging.debug(f"Updated emotional state: {self.state.to_dict()}")
        except Exception as e:
            self.handle_error(e)
            raise UpdateError("Failed to update emotional state.") from e
    
    def regulate(self, strategy: str, emotion_label: str = None, value: float = None) -> None:
        """
        Regulate the emotional state using a specified strategy.
        
        Args:
            strategy (str): The regulation strategy to apply ('neutralize', 'increase', 'decrease', 'toggle').
            emotion_label (str, optional): The emotion to regulate (required for 'increase' and 'decrease').
            value (float, optional): The value to set or adjust the intensity to (required for 'set' operations).
        
        Raises:
            RegulationError: If the regulation strategy is invalid or fails.
        """
        try:
            if strategy not in self.regulation_strategies:
                raise ValueError(f"Regulation strategy '{strategy}' is not supported.")
            
            if strategy == 'neutralize':
                self.state.emotion_label = 'neutral'
                self.state.intensity = 0.0
                logging.info("Applied regulation strategy: neutralize")
            elif strategy == 'increase':
                if not emotion_label:
                    raise ValueError("Missing 'emotion_label' for 'increase' strategy.")
                if emotion_label not in self.allowed_emotions:
                    raise ValueError(f"Emotion '{emotion_label}' is not allowed in this model.")
                if value is None:
                    raise ValueError("Missing 'value' for 'increase' strategy.")
                if not (0.0 <= value <= 1.0):
                    raise ValueError("Value must be between 0.0 and 1.0.")
                if self.state.emotion_label == emotion_label:
                    self.state.intensity = min(self.state.intensity + value, 1.0)
                else:
                    self.state.emotion_label = emotion_label
                    self.state.intensity = value
                logging.info(f"Applied regulation strategy: increase '{emotion_label}' by {value}")
            elif strategy == 'decrease':
                if not emotion_label:
                    raise ValueError("Missing 'emotion_label' for 'decrease' strategy.")
                if emotion_label not in self.allowed_emotions:
                    raise ValueError(f"Emotion '{emotion_label}' is not allowed in this model.")
                if value is None:
                    raise ValueError("Missing 'value' for 'decrease' strategy.")
                if not (0.0 <= value <= 1.0):
                    raise ValueError("Value must be between 0.0 and 1.0.")
                if self.state.emotion_label == emotion_label:
                    self.state.intensity = max(self.state.intensity - value, 0.0)
                    if self.state.intensity == 0.0:
                        self.state.emotion_label = 'neutral'
                logging.info(f"Applied regulation strategy: decrease '{emotion_label}' by {value}")
            elif strategy == 'toggle':
                if self.state.emotion_label != 'neutral':
                    self.state.emotion_label = 'neutral'
                    self.state.intensity = 0.0
                    logging.info("Applied regulation strategy: toggle to 'neutral'")
                else:
                    raise ValueError("Cannot toggle 'neutral' to another emotion without specifying.")
            else:
                raise ValueError(f"Unknown regulation strategy: {strategy}")
        except Exception as e:
            self.handle_error(e)
            raise RegulationError(f"Failed to apply regulation strategy: {strategy}") from e
    
    def express(self) -> str:
        """
        Generate a textual expression of the current emotional state.
        
        Returns:
            str: A string describing the current emotion.
        """
        if self.state.emotion_label == 'neutral' or self.state.intensity == 0.0:
            return "I'm feeling neutral."
        else:
            # Optionally, adjust the expression based on intensity
            intensity_description = ""
            if self.state.intensity >= 0.75:
                intensity_description = " intensely"
            elif self.state.intensity >= 0.5:
                intensity_description = ""
            else:
                intensity_description = " slightly"
            
            return f"I feel{intensity_description} {self.state.emotion_label}."
    
    def serialize(self) -> str:
        """
        Serialize the current emotional state to a JSON string.
        
        Returns:
            str: Serialized emotional state.
        """
        return json.dumps(self.state.to_dict())
    
    def deserialize(self, data: str) -> None:
        """
        Deserialize the emotional state from a JSON string.
        
        Args:
            data (str): Serialized emotional state.
        """
        try:
            state_dict = json.loads(data)
            self.state = CategoryEmotionState.from_dict(state_dict)
            logging.info("Deserialized emotional state.")
        except Exception as e:
            self.handle_error(e)
            raise UpdateError("Failed to deserialize emotional state.") from e

# File: main_category_emotion.py

import asyncio
from aeiva.cognition.emotion.emotion_category import CategoryEmotion

async def main():
    # Configuration for CategoryEmotion
    config = {
        'allowed_emotions': [
            # Positive Emotions
            'admiration', 'amusement', 'approval', 'caring', 'desire', 'excitement',
            'gratitude', 'joy', 'love', 'optimism', 'pride', 'relief',
            # Negative Emotions
            'anger', 'annoyance', 'disappointment', 'disapproval', 'disgust',
            'embarrassment', 'fear', 'grief', 'nervousness', 'remorse', 'sadness',
            # Ambiguous Emotions
            'confusion', 'curiosity', 'realization', 'surprise', 'awe',
            # Additional Emotions
            'frustration', 'hope', 'guilt', 'contentment', 'boredom',
            'loneliness', 'elation'
        ],
        'regulation_strategies': ['neutralize', 'increase', 'decrease', 'toggle'],
        'default_emotions': {
            'emotion_label': 'neutral',
            'intensity': 0.0
        }
    }

    # Instantiate and set up the emotion system
    emotion_system = CategoryEmotion(config)
    await emotion_system.setup()

    # Express initial state
    print(emotion_system.express())  # Output: I'm feeling neutral.

    # Update with stimuli: high joy
    await emotion_system.update({
        'emotion_label': 'joy',
        'intensity': 0.8
    })
    print(emotion_system.express())  # Output: I feel intensely joy.

    # Update with stimuli: moderate curiosity
    await emotion_system.update({
        'emotion_label': 'curiosity',
        'intensity': 0.5
    })
    print(emotion_system.express())  # Output: I feel intensely curiosity.

    # Apply regulation: decrease intensity of 'curiosity' by 0.3
    emotion_system.regulate('decrease', emotion_label='curiosity', value=0.3)
    print(emotion_system.express())  # Output: I feel slightly curiosity.

    # Apply regulation: neutralize emotions
    emotion_system.regulate('neutralize')
    print(emotion_system.express())  # Output: I'm feeling neutral.

    # Serialize the emotional state
    serialized_state = emotion_system.serialize()
    print(f"Serialized State: {serialized_state}")

    # Deserialize into a new emotion system instance
    new_emotion_system = CategoryEmotion(config)
    await new_emotion_system.setup()
    new_emotion_system.deserialize(serialized_state)
    print(new_emotion_system.express())  # Output: I'm feeling neutral.

    # Example of toggling emotion
    await emotion_system.update({
        'emotion_label': 'hope',
        'intensity': 0.6
    })
    print(emotion_system.express())  # Output: I feel hope.
    
    emotion_system.regulate('toggle')
    print(emotion_system.express())  # Output: I'm feeling neutral.

    # Example of increasing an emotion's intensity
    emotion_system.regulate('increase', emotion_label='hope', value=0.3)
    print(emotion_system.express())  # Output: I feel intensely hope.

if __name__ == '__main__':
    asyncio.run(main())
