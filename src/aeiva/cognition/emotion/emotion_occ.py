# File: cognition/emotion_occ.py

from typing import Dict, Any

class OCCEmotionState:
    """
    Represents the emotional state in the OCC Appraisal-Based Model.
    """
    def __init__(self, emotion_categories: Dict[str, float] = None):
        """
        Initialize the OCC emotion state with emotion categories and their intensities.
        """
        # Initialize with zero intensities if not provided
        self.emotion_categories = emotion_categories if emotion_categories else {
            'joy': 0.0,
            'sadness': 0.0,
            'anger': 0.0,
            'fear': 0.0,
            'surprise': 0.0,
            'disgust': 0.0
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            'emotion_categories': self.emotion_categories
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        return OCCEmotionState(
            emotion_categories=data.get('emotion_categories', {})
        )

# File: cognition/emotion_occ.py

from typing import Dict, Any
from aeiva.cognition.emotion.emotion import Emotion, ConfigurationError, UpdateError, RegulationError
import asyncio
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCCEmotion(Emotion[OCCEmotionState]):
    """
    Concrete implementation of the Emotion base class using the OCC Appraisal-Based Model.
    """

    # Define emotion categories based on OCC theory
    PRIMARY_EMOTIONS = {'joy', 'sadness', 'anger', 'fear', 'surprise', 'disgust'}

    def init_state(self) -> OCCEmotionState:
        """
        Initialize the emotional state with zero intensities for all categories.
        """
        return OCCEmotionState()

    async def setup(self) -> None:
        """
        Set up the OCC Emotion system.
        """
        required_keys = ['appraisal_weights']
        for key in required_keys:
            if key not in self.config:
                raise ConfigurationError(f"Missing configuration parameter: {key}")

        # Initialize appraisal weights
        self.appraisal_weights = self.config['appraisal_weights']  # e.g., {'desirability': 0.5, ...}
        logging.info("OCCEmotion setup complete.")

    async def update(self, input_data: Dict[str, Any]) -> None:
        """
        Update the emotional state based on input stimuli using appraisal.
        """
        try:
            # Simplified appraisal: assume input_data contains 'desirability', 'praiseworthiness', 'obligation'
            desirability = input_data.get('desirability', 0.0) * self.appraisal_weights.get('desirability', 0.0)
            praiseworthiness = input_data.get('praiseworthiness', 0.0) * self.appraisal_weights.get('praiseworthiness', 0.0)
            obligation = input_data.get('obligation', 0.0) * self.appraisal_weights.get('obligation', 0.0)

            # Update emotion categories based on appraisal
            self.state.emotion_categories['joy'] += desirability
            self.state.emotion_categories['anger'] += -desirability if desirability < 0 else 0.0
            self.state.emotion_categories['sadness'] += -desirability if desirability < 0 else 0.0

            self.state.emotion_categories['anger'] += praiseworthiness if praiseworthiness < 0 else 0.0
            self.state.emotion_categories['joy'] += praiseworthiness if praiseworthiness > 0 else 0.0

            self.state.emotion_categories['fear'] += obligation if obligation > 0 else 0.0
            self.state.emotion_categories['disgust'] += obligation if obligation < 0 else 0.0

            # Normalize emotion intensities to stay within [0, 1]
            for emotion, intensity in self.state.emotion_categories.items():
                self.state.emotion_categories[emotion] = max(min(intensity, 1.0), 0.0)

            logging.debug(f"Updated emotional state: {self.state.to_dict()}")
        except Exception as e:
            self.handle_error(e)
            raise UpdateError("Failed to update emotional state.") from e

    def regulate(self, strategy: str) -> None:
        """
        Regulate the emotional state using a specified strategy.
        """
        try:
            if strategy == 'neutralize':
                for emotion in self.state.emotion_categories:
                    self.state.emotion_categories[emotion] = 0.0
            elif strategy == 'intensify':
                for emotion in self.state.emotion_categories:
                    self.state.emotion_categories[emotion] *= 1.2
                    self.state.emotion_categories[emotion] = min(self.state.emotion_categories[emotion], 1.0)
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
        dominant_emotion = max(self.state.emotion_categories, key=self.state.emotion_categories.get)
        expressions = {
            'joy': "I feel joyful!",
            'sadness': "I feel sad.",
            'anger': "I feel angry!",
            'fear': "I feel fearful.",
            'surprise': "I feel surprised!",
            'disgust': "I feel disgusted."
        }
        return expressions.get(dominant_emotion, "I'm feeling neutral.")

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
            self.state = OCCEmotionState.from_dict(state_dict)
            logging.info("Deserialized emotional state.")
        except Exception as e:
            self.handle_error(e)
            raise UpdateError("Failed to deserialize emotional state.") from e

# File: main_occ.py

import asyncio
from aeiva.cognition.emotion.emotion_occ import OCCEmotion

async def main():
    config = {
        'appraisal_weights': {
            'desirability': 0.5,
            'praiseworthiness': 0.3,
            'obligation': 0.2
        }
    }
    emotion_system = OCCEmotion(config)
    await emotion_system.setup()

    print(emotion_system.express())  # Output: I'm feeling neutral.

    # Simulate a desirable event
    await emotion_system.update({
        'desirability': 0.8,          # Positive impact
        'praiseworthiness': 0.0,
        'obligation': 0.0
    })
    print(emotion_system.express())  # Output: I feel joyful!

    # Simulate an obligation (fear)
    await emotion_system.update({
        'desirability': 0.0,
        'praiseworthiness': 0.0,
        'obligation': 0.6            # Positive obligation leads to fear
    })
    print(emotion_system.express())  # Output may vary based on dominance of emotions

    # Regulate emotions
    emotion_system.regulate('neutralize')
    print(emotion_system.express())  # Output: I'm feeling neutral.

    serialized_state = emotion_system.serialize()
    print(f"Serialized State: {serialized_state}")

    # Deserialize into a new emotion system instance
    new_emotion_system = OCCEmotion(config)
    await new_emotion_system.setup()
    new_emotion_system.deserialize(serialized_state)
    print(new_emotion_system.express())  # Output: I'm feeling neutral.

# Run the test
if __name__ == "__main__":
    asyncio.run(main())