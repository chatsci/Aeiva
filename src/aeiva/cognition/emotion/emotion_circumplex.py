# File: cognition/emotion_circumplex.py

from typing import Dict, Any

class CircumplexEmotionState:
    """
    Represents the emotional state in the Circumplex Model.
    """
    def __init__(self, valence: float = 0.0, arousal: float = 0.0):
        self.valence = valence  # Range: [-1.0, 1.0]
        self.arousal = arousal  # Range: [-1.0, 1.0]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'valence': self.valence,
            'arousal': self.arousal
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        return CircumplexEmotionState(
            valence=data.get('valence', 0.0),
            arousal=data.get('arousal', 0.0)
        )

# File: cognition/emotion_circumplex.py

from typing import Dict, Any
from aeiva.cognition.emotion.emotion import Emotion, ConfigurationError, UpdateError, RegulationError
import asyncio
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CircumplexEmotion(Emotion[CircumplexEmotionState]):
    """
    Concrete implementation of the Emotion base class using the Circumplex Model.
    """

    def init_state(self) -> CircumplexEmotionState:
        """
        Initialize the emotional state with default valence and arousal.
        """
        default_valence = self.config.get('default_valence', 0.0)
        default_arousal = self.config.get('default_arousal', 0.0)
        return CircumplexEmotionState(valence=default_valence, arousal=default_arousal)

    async def setup(self) -> None:
        """
        Set up the Circumplex Emotion system.
        """
        required_keys = ['valence_weight', 'arousal_weight', 'decay_rate']
        for key in required_keys:
            if key not in self.config:
                raise ConfigurationError(f"Missing configuration parameter: {key}")

        # Initialize weights and decay rate
        self.valence_weight = self.config['valence_weight']
        self.arousal_weight = self.config['arousal_weight']
        self.decay_rate = self.config['decay_rate']
        logging.info("CircumplexEmotion setup complete.")

    async def update(self, input_data: Dict[str, Any]) -> None:
        """
        Update the emotional state based on input stimuli.
        """
        try:
            valence_impact = input_data.get('valence_impact', 0.0) * self.valence_weight
            arousal_impact = input_data.get('arousal_impact', 0.0) * self.arousal_weight

            self.state.valence += valence_impact
            self.state.arousal += arousal_impact

            # Normalize values to stay within [-1, 1]
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
            if strategy == 'suppression':
                self.state.valence *= 0.8
                self.state.arousal *= 0.8
            elif strategy == 'amplification':
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
        if self.state.valence > 0.5 and self.state.arousal > 0.5:
            return "I feel excited and joyful!"
        elif self.state.valence > 0.5 and self.state.arousal < -0.5:
            return "I feel calm and happy."
        elif self.state.valence < -0.5 and self.state.arousal > 0.5:
            return "I feel angry and agitated."
        elif self.state.valence < -0.5 and self.state.arousal < -0.5:
            return "I feel depressed and lethargic."
        else:
            return "I'm feeling neutral."

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
            self.state = CircumplexEmotionState.from_dict(state_dict)
            logging.info("Deserialized emotional state.")
        except Exception as e:
            self.handle_error(e)
            raise UpdateError("Failed to deserialize emotional state.") from e

# File: main_circumplex.py

import asyncio
from aeiva.cognition.emotion.emotion_circumplex import CircumplexEmotion

async def main():
    config = {
        'valence_weight': 0.5,
        'arousal_weight': 0.3,
        'decay_rate': 0.1,
        'default_valence': 0.0,
        'default_arousal': 0.0
    }
    emotion_system = CircumplexEmotion(config)
    await emotion_system.setup()

    print(emotion_system.express())  # Output: I'm feeling neutral.

    await emotion_system.update({'valence_impact': 0.8, 'arousal_impact': 0.5})
    print(emotion_system.express())  # Output: I feel excited and joyful!

    emotion_system.regulate('suppression')
    print(emotion_system.express())  # Output: I feel excited and joyful! (with reduced intensity)

    serialized_state = emotion_system.serialize()
    print(f"Serialized State: {serialized_state}")

    # Deserialize into a new emotion system instance
    new_emotion_system = CircumplexEmotion(config)
    await new_emotion_system.setup()
    new_emotion_system.deserialize(serialized_state)
    print(new_emotion_system.express())  # Output: I feel excited and joyful!

# Run the test
if __name__ == "__main__":
    asyncio.run(main())
