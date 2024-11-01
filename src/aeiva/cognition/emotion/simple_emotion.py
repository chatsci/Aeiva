# File: cognition/simple_emotion.py

from aeiva.cognition.emotion.emotion import Emotion
from typing import Any, Dict, Optional


class SimpleEmotion:

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # super().__init__(config)
        self.state = self.init_state()

    def init_state(self) -> str:
        return 'neutral'

    def setup(self) -> None:
        print("SimpleEmotion system setup complete.")

    async def update(self, input_data: Any) -> None:
        # Basic logic to determine emotion based on input_data
        if isinstance(input_data, dict):
            if 'event' in input_data:
                event = input_data['event']
                
                if event == 'success':
                    self.state = 'happy'
                elif event == 'failure':
                    self.state = 'sad'
                elif event == 'threat':
                    self.state = 'angry'
                elif event == 'support':
                    self.state = 'grateful'
                else:
                    self.state = 'neutral'
            else:
                self.state = 'neutral'
        else:
            self.state = 'neutral'

        print(f"Emotion updated to: {self.state}")

    def get_current_state(self) -> str:
        return self.state