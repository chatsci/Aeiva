# File: cognition/emotion_componential.py

from dataclasses import dataclass, field
from typing import Dict, Any
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ComponentialEmotionState:
    """
    Represents the emotional state based on the Componential Model.
    
    Attributes:
        emotion_label (str): Current emotion category.
        intensity (float): Intensity of the emotion (0.0 to 1.0).
    """
    emotion_label: str = "neutral"
    intensity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'emotion_label': self.emotion_label,
            'intensity': self.intensity
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        return ComponentialEmotionState(
            emotion_label=data.get('emotion_label', 'neutral'),
            intensity=data.get('intensity', 0.0)
        )

from typing import Dict, Any
from aeiva.cognition.emotion.emotion import Emotion, ConfigurationError, UpdateError, RegulationError
import asyncio

class ComponentialEmotion(Emotion[ComponentialEmotionState]):
    """
    Concrete implementation of the Emotion base class using the Componential Model.
    """
    
    # Define possible emotions
    EMOTIONS = {
        'joy', 'sadness', 'anger', 'fear', 'surprise', 'disgust',
        'trust', 'anticipation', 'contentment', 'frustration'
    }
    
    def init_state(self) -> ComponentialEmotionState:
        default_emotion = self.config.get('default_emotion', 'neutral')
        default_intensity = self.config.get('default_intensity', 0.0)
        if default_emotion not in self.EMOTIONS and default_emotion != 'neutral':
            raise ConfigurationError(f"Invalid default emotion: {default_emotion}")
        return ComponentialEmotionState(emotion_label=default_emotion, intensity=default_intensity)
    
    async def setup(self) -> None:
        """
        Set up the Componential Emotion system.
        """
        required_keys = ['appraisal_weights', 'decay_rate']
        for key in required_keys:
            if key not in self.config:
                raise ConfigurationError(f"Missing configuration parameter: {key}")
        
        self.appraisal_weights = self.config['appraisal_weights']  # e.g., {'relevance': 0.3, ...}
        self.decay_rate = self.config['decay_rate']
        
        logging.info("ComponentialEmotion setup complete.")
    
    async def update(self, input_data: Dict[str, Any]) -> None:
        """
        Update the emotional state based on input stimuli via appraisal.
        """
        try:
            # Extract appraisal factors
            relevance = input_data.get('relevance', 0.0) * self.appraisal_weights.get('relevance', 0.0)
            implication = input_data.get('implication', 0.0) * self.appraisal_weights.get('implication', 0.0)
            causality = input_data.get('causality', 0.0) * self.appraisal_weights.get('causality', 0.0)
            control = input_data.get('control', 0.0) * self.appraisal_weights.get('control', 0.0)
            future_expectation = input_data.get('future_expectation', 0.0) * self.appraisal_weights.get('future_expectation', 0.0)
            
            # Simple mapping logic to determine emotion based on appraisal
            total = relevance + implication + causality + control + future_expectation
            
            if total > 2.0:
                emotion = 'joy'
            elif 1.5 < total <= 2.0:
                emotion = 'anticipation'
            elif 1.0 < total <= 1.5:
                emotion = 'trust'
            elif 0.5 < total <= 1.0:
                emotion = 'surprise'
            else:
                emotion = 'sadness'
            
            self.state.emotion_label = emotion
            self.state.intensity = min(total / 3.0, 1.0)  # Normalize intensity
            
            logging.debug(f"Appraisal results: {total}, Mapped Emotion: {emotion}, Intensity: {self.state.intensity}")
        except Exception as e:
            self.handle_error(e)
            raise UpdateError("Failed to update emotional state via appraisal.") from e
    
    def regulate(self, strategy: str) -> None:
        """
        Regulate the emotional state using a specified strategy.
        """
        try:
            if strategy == 'decay':
                self.state.intensity = max(self.state.intensity - self.decay_rate, 0.0)
                if self.state.intensity == 0.0:
                    self.state.emotion_label = 'neutral'
                logging.info("Applied regulation strategy: decay")
            elif strategy == 'reset':
                self.state.emotion_label = 'neutral'
                self.state.intensity = 0.0
                logging.info("Applied regulation strategy: reset")
            else:
                raise ValueError(f"Unknown regulation strategy: {strategy}")
        except Exception as e:
            self.handle_error(e)
            raise RegulationError(f"Failed to apply regulation strategy: {strategy}") from e
    
    def express(self) -> str:
        """
        Generate a textual expression of the current emotional state.
        """
        if self.state.emotion_label == 'neutral' or self.state.intensity == 0.0:
            return "I'm feeling neutral."
        else:
            intensity_desc = ""
            if self.state.intensity > 0.7:
                intensity_desc = " intensely"
            elif self.state.intensity > 0.4:
                intensity_desc = ""
            else:
                intensity_desc = " slightly"
            return f"I feel{intensity_desc} {self.state.emotion_label}."
    
    def serialize(self) -> str:
        return json.dumps(self.state.to_dict())
    
    def deserialize(self, data: str) -> None:
        try:
            state_dict = json.loads(data)
            self.state = ComponentialEmotionState.from_dict(state_dict)
            logging.info("Deserialized Componential emotional state.")
        except Exception as e:
            self.handle_error(e)
            raise UpdateError("Failed to deserialize Componential emotional state.") from e

# File: main_componential.py

import asyncio
from aeiva.cognition.emotion.emotion_componential import ComponentialEmotion

async def main():
    # Configuration for ComponentialEmotion
    config = {
        'appraisal_weights': {
            'relevance': 0.5,
            'implication': 0.4,
            'causality': 0.3,
            'control': 0.2,
            'future_expectation': 0.1
        },
        'decay_rate': 0.2,  # Intensity decreases by 0.2 on decay
        'default_emotions': {
            'emotion_label': 'neutral',
            'intensity': 0.0
        }
    }

    # Instantiate and set up the emotion system
    emotion_system = ComponentialEmotion(config)
    await emotion_system.setup()

    # Express initial state
    print(emotion_system.express())  # Output: I'm feeling neutral.

    # Update with stimuli: high relevance and implication
    await emotion_system.update({
        'relevance': 2.0,
        'implication': 1.5,
        'causality': 0.5,
        'control': 0.3,
        'future_expectation': 0.2
    })
    print(emotion_system.express())  # Output: I feel joy. or similar based on mapping

    # Apply regulation: decay
    emotion_system.regulate('decay')
    print(emotion_system.express())  # Output may vary based on updated intensity

    # Apply regulation: reset
    emotion_system.regulate('reset')
    print(emotion_system.express())  # Output: I'm feeling neutral.

    # Serialize the emotional state
    serialized_state = emotion_system.serialize()
    print(f"Serialized State: {serialized_state}")

    # Deserialize into a new emotion system instance
    new_emotion_system = ComponentialEmotion(config)
    await new_emotion_system.setup()
    new_emotion_system.deserialize(serialized_state)
    print(new_emotion_system.express())  # Output matches the serialized state

if __name__ == '__main__':
    asyncio.run(main())