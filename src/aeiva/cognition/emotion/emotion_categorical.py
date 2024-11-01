# File: cognition/emotion_categorical.py

from typing import Dict, Any

class CategoricalEmotionState:
    """
    Represents the emotional state in a Categorical Model.
    """
    def __init__(self, emotion_label: str = "neutral"):
        self.emotion_label = emotion_label

    def to_dict(self) -> Dict[str, Any]:
        return {
            'emotion_label': self.emotion_label
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        return CategoricalEmotionState(
            emotion_label=data.get('emotion_label', 'neutral')
        )

# File: cognition/emotion_categorical.py

from typing import Dict, Any
from aeiva.cognition.emotion.emotion import Emotion, ConfigurationError, UpdateError, RegulationError
import asyncio
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CategoricalEmotion(Emotion[CategoricalEmotionState]):
    """
    Concrete implementation of the Emotion base class using a Categorical Model.
    """

    VALID_EMOTIONS = {'happy', 'sad', 'angry', 'fearful', 'surprised', 'disgusted', 'neutral'}

    def init_state(self) -> CategoricalEmotionState:
        """
        Initialize the emotional state with a default emotion.
        """
        default_emotion = self.config.get('default_emotion', 'neutral')
        if default_emotion not in self.VALID_EMOTIONS:
            raise ConfigurationError(f"Invalid default emotion: {default_emotion}")
        return CategoricalEmotionState(emotion_label=default_emotion)

    async def setup(self) -> None:
        """
        Set up the Categorical Emotion system.
        """
        required_keys = ['default_emotion']
        for key in required_keys:
            if key not in self.config:
                raise ConfigurationError(f"Missing configuration parameter: {key}")

        default_emotion = self.config['default_emotion']
        if default_emotion not in self.VALID_EMOTIONS:
            raise ConfigurationError(f"Invalid default emotion: {default_emotion}")

        self.state.emotion_label = default_emotion
        logging.info("CategoricalEmotion setup complete.")

    async def update(self, input_data: Dict[str, Any]) -> None:
        """
        Update the emotional state based on input stimuli.
        """
        try:
            new_emotion = input_data.get('emotion_label')
            if new_emotion and new_emotion in self.VALID_EMOTIONS:
                self.state.emotion_label = new_emotion
                logging.debug(f"Updated emotional state: {self.state.to_dict()}")
            else:
                raise ValueError(f"Invalid or missing emotion_label: {new_emotion}")
        except Exception as e:
            self.handle_error(e)
            raise UpdateError("Failed to update emotional state.") from e

    def regulate(self, strategy: str) -> None:
        """
        Regulate the emotional state using a specified strategy.
        """
        try:
            if strategy == 'neutralize':
                self.state.emotion_label = 'neutral'
                logging.info("Applied regulation strategy: neutralize")
            elif strategy == 'toggle_positive':
                if self.state.emotion_label == 'neutral':
                    self.state.emotion_label = 'happy'
                elif self.state.emotion_label == 'happy':
                    self.state.emotion_label = 'neutral'
                logging.info("Applied regulation strategy: toggle_positive")
            else:
                raise ValueError(f"Unknown regulation strategy: {strategy}")
        except Exception as e:
            self.handle_error(e)
            raise RegulationError(f"Failed to apply regulation strategy: {strategy}") from e

    def express(self) -> str:
        """
        Generate a textual expression of the current emotional state.
        """
        expressions = {
            'happy': "I feel happy!",
            'sad': "I feel sad.",
            'angry': "I feel angry!",
            'fearful': "I feel fearful.",
            'surprised': "I feel surprised!",
            'disgusted': "I feel disgusted.",
            'neutral': "I'm feeling neutral."
        }
        return expressions.get(self.state.emotion_label, "I'm feeling neutral.")

    def serialize(self) -> str:
        """
        Serialize the current emotional state to a JSON string.
        """
        return json.dumps(self.state.to_dict())

    def deserialize(self, data: str) -> None:
        """
        Deserialize the emotional state from a JSON string.
        """
        try:
            state_dict = json.loads(data)
            self.state = CategoricalEmotionState.from_dict(state_dict)
            logging.info("Deserialized emotional state.")
        except Exception as e:
            self.handle_error(e)
            raise UpdateError("Failed to deserialize emotional state.") from e



# File: main.py

import asyncio
from aeiva.cognition.emotion.emotion_categorical import CategoricalEmotion

async def main():
    config = {'default_emotion': 'neutral'}
    emotion_system = CategoricalEmotion(config)
    await emotion_system.setup()

    print(emotion_system.express())  # Output: I'm feeling neutral.

    await emotion_system.update({'emotion_label': 'happy'})
    print(emotion_system.express())  # Output: I feel happy!

    emotion_system.regulate('neutralize')
    print(emotion_system.express())  # Output: I'm feeling neutral.

    serialized_state = emotion_system.serialize()
    print(f"Serialized State: {serialized_state}")

    # Deserialize into a new emotion system instance
    new_emotion_system = CategoricalEmotion(config)
    await new_emotion_system.setup()
    new_emotion_system.deserialize(serialized_state)
    print(new_emotion_system.express())  # Output: I'm feeling neutral.

# Run the test
if __name__ == "__main__":
    asyncio.run(main())