# File: cognition/emotion_plutchik.py

from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class PlutchikEmotionState:
    """
    Represents the emotional state in Plutchik's Wheel of Emotions.
    
    Attributes:
        joy (float): Intensity of Joy.
        trust (float): Intensity of Trust.
        fear (float): Intensity of Fear.
        surprise (float): Intensity of Surprise.
        sadness (float): Intensity of Sadness.
        disgust (float): Intensity of Disgust.
        anger (float): Intensity of Anger.
        anticipation (float): Intensity of Anticipation.
    """
    joy: float = 0.0
    trust: float = 0.0
    fear: float = 0.0
    surprise: float = 0.0
    sadness: float = 0.0
    disgust: float = 0.0
    anger: float = 0.0
    anticipation: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'joy': self.joy,
            'trust': self.trust,
            'fear': self.fear,
            'surprise': self.surprise,
            'sadness': self.sadness,
            'disgust': self.disgust,
            'anger': self.anger,
            'anticipation': self.anticipation
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        return PlutchikEmotionState(
            joy=data.get('joy', 0.0),
            trust=data.get('trust', 0.0),
            fear=data.get('fear', 0.0),
            surprise=data.get('surprise', 0.0),
            sadness=data.get('sadness', 0.0),
            disgust=data.get('disgust', 0.0),
            anger=data.get('anger', 0.0),
            anticipation=data.get('anticipation', 0.0)
        )

# File: cognition/emotion_plutchik.py

from typing import Dict, Any
from aeiva.cognition.emotion.emotion import Emotion, ConfigurationError, UpdateError, RegulationError
import asyncio
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlutchikEmotion(Emotion[PlutchikEmotionState]):
    """
    Concrete implementation of the Emotion base class using Plutchik's Wheel of Emotions.
    """

    # Define the primary emotions as per Plutchik's model
    PRIMARY_EMOTIONS = {
        'joy': 'joy',
        'trust': 'trust',
        'fear': 'fear',
        'surprise': 'surprise',
        'sadness': 'sadness',
        'disgust': 'disgust',
        'anger': 'anger',
        'anticipation': 'anticipation'
    }

    def init_state(self) -> PlutchikEmotionState:
        """
        Initialize the emotional state with default intensities.
        """
        default_emotions = self.config.get('default_emotions', {})
        return PlutchikEmotionState(
            joy=default_emotions.get('joy', 0.0),
            trust=default_emotions.get('trust', 0.0),
            fear=default_emotions.get('fear', 0.0),
            surprise=default_emotions.get('surprise', 0.0),
            sadness=default_emotions.get('sadness', 0.0),
            disgust=default_emotions.get('disgust', 0.0),
            anger=default_emotions.get('anger', 0.0),
            anticipation=default_emotions.get('anticipation', 0.0)
        )

    async def setup(self) -> None:
        """
        Set up the Plutchik Emotion system.
        
        Raises:
            ConfigurationError: If required configuration parameters are missing or invalid.
        """
        required_keys = ['emotion_weights', 'decay_rate']
        for key in required_keys:
            if key not in self.config:
                raise ConfigurationError(f"Missing configuration parameter: {key}")

        # Initialize emotion weights and decay rate
        self.emotion_weights = self.config['emotion_weights']  # e.g., {'joy': 0.5, 'fear': 0.3, ...}
        self.decay_rate = self.config['decay_rate']  # Float indicating decay per update cycle

        # Validate emotion weights
        for emotion in self.PRIMARY_EMOTIONS:
            if emotion not in self.emotion_weights:
                raise ConfigurationError(f"Missing weight for emotion: {emotion}")
            if not (0.0 <= self.emotion_weights[emotion] <= 1.0):
                raise ConfigurationError(f"Invalid weight for emotion {emotion}: {self.emotion_weights[emotion]}")

        logging.info("PlutchikEmotion setup complete.")

    async def update(self, input_data: Dict[str, Any]) -> None:
        """
        Update the emotional state based on input stimuli.

        Args:
            input_data (Dict[str, Any]): Stimuli data affecting emotions.
                Expected keys can include any of the primary emotions with their impact values.

        Raises:
            UpdateError: If updating the emotional state fails.
        """
        try:
            # Update each emotion based on input_data and corresponding weights
            for emotion in self.PRIMARY_EMOTIONS:
                impact = input_data.get(emotion, 0.0) * self.emotion_weights.get(emotion, 0.0)
                current_intensity = getattr(self.state, emotion)
                new_intensity = current_intensity + impact

                # Clamp the intensity between 0.0 and 1.0
                new_intensity = max(min(new_intensity, 1.0), 0.0)
                setattr(self.state, emotion, new_intensity)

            self.balance_opposite_emotions()

            logging.debug(f"Updated emotional state: {self.state.to_dict()}")
        except Exception as e:
            self.handle_error(e)
            raise UpdateError("Failed to update emotional state.") from e
    
    def balance_opposite_emotions(self):
        """
        Ensure that opposite emotions are balanced to prevent conflicting intensities.
        """
        opposite_pairs = [
            ('joy', 'sadness'),
            ('trust', 'disgust'),
            ('fear', 'anger'),
            ('surprise', 'anticipation')
        ]

        for emotion1, emotion2 in opposite_pairs:
            intensity1 = getattr(self.state, emotion1)
            intensity2 = getattr(self.state, emotion2)
            if intensity1 > 0.6 and intensity2 > 0.6:
                # Reduce the weaker emotion
                if intensity1 > intensity2:
                    setattr(self.state, emotion2, intensity2 * 0.5)
                else:
                    setattr(self.state, emotion1, intensity1 * 0.5)

    def regulate(self, strategy: str) -> None:
        """
        Regulate the emotional state using a specified strategy.

        Args:
            strategy (str): The regulation strategy to apply (e.g., 'decay', 'intensify').

        Raises:
            RegulationError: If the regulation strategy is invalid or fails.
        """
        try:
            if strategy == 'decay':
                # Gradually reduce each emotion's intensity
                for emotion in self.PRIMARY_EMOTIONS:
                    current_intensity = getattr(self.state, emotion)
                    new_intensity = current_intensity * (1 - self.decay_rate)
                    setattr(self.state, emotion, max(new_intensity, 0.0))
                logging.info("Applied regulation strategy: decay")
            elif strategy == 'intensify':
                # Increase each emotion's intensity by a fixed factor
                for emotion in self.PRIMARY_EMOTIONS:
                    current_intensity = getattr(self.state, emotion)
                    new_intensity = current_intensity * 1.2
                    setattr(self.state, emotion, min(new_intensity, 1.0))
                logging.info("Applied regulation strategy: intensify")
            elif strategy.startswith('set_'):
                # Example: strategy = 'set_joy', value = 0.8
                emotion, value = strategy.split('_')[1], float(strategy.split('_')[2])
                if emotion in self.PRIMARY_EMOTIONS and 0.0 <= value <= 1.0:
                    setattr(self.state, emotion, value)
                    logging.info(f"Set {emotion} intensity to {value}")
                else:
                    raise ValueError(f"Invalid strategy or value: {strategy}")
            else:
                raise ValueError(f"Unknown regulation strategy: {strategy}")
        except Exception as e:
            self.handle_error(e)
            raise RegulationError(f"Failed to apply regulation strategy: {strategy}") from e

    def express(self) -> str:
        """
        Generate a textual expression of the current emotional state.

        Returns:
            str: A string describing the current emotion(s).
        """
        # Determine dominant emotions
        emotion_intensities = self.state.to_dict()
        dominant_emotions = [emotion for emotion, intensity in emotion_intensities.items() if intensity > 0.6]

        if dominant_emotions:
            return f"I feel {' and '.join(dominant_emotions)}!"
        else:
            return "I'm feeling neutral."

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
            self.state = PlutchikEmotionState.from_dict(state_dict)
            logging.info("Deserialized emotional state.")
        except Exception as e:
            self.handle_error(e)
            raise UpdateError("Failed to deserialize emotional state.") from e

# File: main_plutchik.py

import asyncio
from aeiva.cognition.emotion.emotion_plutchik import PlutchikEmotion

async def main():
    # Configuration for PlutchikEmotion
    config = {
        'emotion_weights': {
            'joy': 0.5,
            'trust': 0.3,
            'fear': 0.4,
            'surprise': 0.2,
            'sadness': 0.4,
            'disgust': 0.3,
            'anger': 0.5,
            'anticipation': 0.3
        },
        'decay_rate': 0.1,  # 10% decay per regulation cycle
        'default_emotions': {
            'joy': 0.0,
            'trust': 0.0,
            'fear': 0.0,
            'surprise': 0.0,
            'sadness': 0.0,
            'disgust': 0.0,
            'anger': 0.0,
            'anticipation': 0.0
        }
    }

    # Instantiate and set up the emotion system
    emotion_system = PlutchikEmotion(config)
    await emotion_system.setup()

    # Express initial state
    print(emotion_system.express())  # Output: I'm feeling neutral.

    # Update with stimuli: high joy and moderate trust
    await emotion_system.update({
        'joy': 0.8,          # High impact on joy
        'trust': 0.5         # Moderate impact on trust
    })
    print(emotion_system.express())  # Output: I feel joy and trust!

    # Apply regulation: decay
    emotion_system.regulate('decay')
    print(emotion_system.express())  # Output may vary based on updated intensities

    # Apply regulation: intensify
    emotion_system.regulate('intensify')
    print(emotion_system.express())  # Output may vary based on updated intensities

    # Serialize the emotional state
    serialized_state = emotion_system.serialize()
    print(f"Serialized State: {serialized_state}")

    # Deserialize into a new emotion system instance
    new_emotion_system = PlutchikEmotion(config)
    await new_emotion_system.setup()
    new_emotion_system.deserialize(serialized_state)
    print(new_emotion_system.express())  # Output should match the serialized state

# Run the main function
if __name__ == '__main__':
    asyncio.run(main())