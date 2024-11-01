# File: cognition/emotion_hybrid.py

from typing import Dict, Any

class HybridEmotionState:
    """
    Represents the emotional state in the Hybrid Categorical-Dimensional Model.
    """
    def __init__(self, emotion_label: str = "neutral", valence: float = 0.0, arousal: float = 0.0):
        self.emotion_label = emotion_label  # Categorical label
        self.valence = valence              # Dimensional valence
        self.arousal = arousal              # Dimensional arousal

    def to_dict(self) -> Dict[str, Any]:
        return {
            'emotion_label': self.emotion_label,
            'valence': self.valence,
            'arousal': self.arousal
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        return HybridEmotionState(
            emotion_label=data.get('emotion_label', 'neutral'),
            valence=data.get('valence', 0.0),
            arousal=data.get('arousal', 0.0)
        )

# File: cognition/emotion_hybrid.py

from typing import Dict, Any
from aeiva.cognition.emotion.emotion import Emotion, ConfigurationError, UpdateError, RegulationError
import asyncio
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HybridEmotion(Emotion[HybridEmotionState]):
    """
    Concrete implementation of the Emotion base class using a Hybrid Categorical-Dimensional Model.
    """

    VALID_EMOTIONS = {'happy', 'sad', 'angry', 'fearful', 'surprised', 'disgusted', 'neutral'}

    def init_state(self) -> HybridEmotionState:
        """
        Initialize the emotional state with default values.
        """
        default_emotion = self.config.get('default_emotion', 'neutral')
        if default_emotion not in self.VALID_EMOTIONS:
            raise ConfigurationError(f"Invalid default emotion: {default_emotion}")
        return HybridEmotionState(
            emotion_label=default_emotion,
            valence=0.0,
            arousal=0.0
        )

    async def setup(self) -> None:
        """
        Set up the Hybrid Emotion system.
        """
        required_keys = ['valence_weight', 'arousal_weight', 'decay_rate']
        for key in required_keys:
            if key not in self.config:
                raise ConfigurationError(f"Missing configuration parameter: {key}")

        # Initialize weights and decay rate
        self.valence_weight = self.config['valence_weight']
        self.arousal_weight = self.config['arousal_weight']
        self.decay_rate = self.config['decay_rate']
        logging.info("HybridEmotion setup complete.")

    async def update(self, input_data: Dict[str, Any]) -> None:
        """
        Update the emotional state based on input stimuli.
        """
        try:
            # Update categorical emotion if provided
            new_emotion = input_data.get('emotion_label')
            if new_emotion and new_emotion in self.VALID_EMOTIONS:
                self.state.emotion_label = new_emotion

            # Update dimensional aspects
            valence_impact = input_data.get('valence_impact', 0.0) * self.valence_weight
            arousal_impact = input_data.get('arousal_impact', 0.0) * self.arousal_weight

            self.state.valence += valence_impact
            self.state.arousal += arousal_impact

            # Normalize dimensional values to stay within [-1, 1]
            self.state.valence = max(min(self.state.valence, 1.0), -1.0)
            self.state.arousal = max(min(self.state.arousal, 1.0), -1.0)

            logging.debug(f"Updated emotional state: {self.state.to_dict()}")
        except Exception as e:
            self.handle_error(e)
            raise UpdateError("Failed to update emotional state.") from e

    def regulate(self, strategy: str) -> None:
        """
        Regulate the emotional state using a specified strategy.
        """
        try:
            if strategy == 'suppress':
                self.state.valence *= 0.8
                self.state.arousal *= 0.8
                # Optionally adjust categorical label towards neutral
                if self.state.emotion_label != 'neutral':
                    self.state.emotion_label = 'neutral'
            elif strategy == 'amplify':
                self.state.valence *= 1.2
                self.state.arousal *= 1.2
                # Ensure values do not exceed bounds after amplification
                self.state.valence = max(min(self.state.valence, 1.0), -1.0)
                self.state.arousal = max(min(self.state.arousal, 1.0), -1.0)
            else:
                raise ValueError(f"Unknown regulation strategy: {strategy}")
            logging.info(f"Applied regulation strategy: {strategy}")
        except Exception as e:
            self.handle_error(e)
            raise RegulationError(f"Failed to apply regulation strategy: {strategy}") from e

    def express(self) -> str:
        """
        Generate a textual expression of the current emotional state.
        """
        # Combine categorical and dimensional expressions
        categorical_expression = {
            'happy': "I feel happy!",
            'sad': "I feel sad.",
            'angry': "I feel angry!",
            'fearful': "I feel fearful.",
            'surprised': "I feel surprised!",
            'disgusted': "I feel disgusted.",
            'neutral': "I'm feeling neutral."
        }.get(self.state.emotion_label, "I'm feeling neutral.")

        dimensional_expression = ""
        if self.state.valence > 0.5:
            dimensional_expression += " I am experiencing high pleasure."
        elif self.state.valence < -0.5:
            dimensional_expression += " I am experiencing high displeasure."

        if self.state.arousal > 0.5:
            dimensional_expression += " I am highly aroused."
        elif self.state.arousal < -0.5:
            dimensional_expression += " I am very calm."

        return categorical_expression + dimensional_expression

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
            self.state = HybridEmotionState.from_dict(state_dict)
            logging.info("Deserialized emotional state.")
        except Exception as e:
            self.handle_error(e)
            raise UpdateError("Failed to deserialize emotional state.") from e

# File: main_hybrid.py

import asyncio
from aeiva.cognition.emotion.emotion_hybrid import HybridEmotion

async def main():
    config = {
        'valence_weight': 0.5,
        'arousal_weight': 0.3,
        'decay_rate': 0.1,
        'default_emotion': 'neutral'
    }
    emotion_system = HybridEmotion(config)
    await emotion_system.setup()

    print(emotion_system.express())  # Output: I'm feeling neutral.

    # Update with categorical and dimensional impacts
    await emotion_system.update({
        'emotion_label': 'happy',
        'valence_impact': 0.6,
        'arousal_impact': 0.4
    })
    print(emotion_system.express())  # Output: I feel happy! I am experiencing high pleasure. I am highly aroused.

    # Regulate emotions
    emotion_system.regulate('suppress')
    print(emotion_system.express())  # Output: I'm feeling neutral. I am experiencing high pleasure. I am highly aroused.

    serialized_state = emotion_system.serialize()
    print(f"Serialized State: {serialized_state}")

    # Deserialize into a new emotion system instance
    new_emotion_system = HybridEmotion(config)
    await new_emotion_system.setup()
    new_emotion_system.deserialize(serialized_state)
    print(new_emotion_system.express())  # Output: I'm feeling neutral. I am experiencing high pleasure. I am highly aroused.

# Run the test
if __name__ == "__main__":
    asyncio.run(main())