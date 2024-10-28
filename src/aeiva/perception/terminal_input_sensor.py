# terminal_input_sensor.py

import asyncio
import threading
import logging
from aeiva.perception.sensor import Sensor


class TerminalInputSensor(Sensor):
    """
    A sensor that reads input from the terminal and emits stimuli via the EventBus.
    """
    def __init__(self, name: str, params: dict, event_bus):
        super().__init__(name, params, event_bus)
        self.prompt_message = params.get('prompt_message', 'You: ')
        self._running = False
        self._thread = None
        # self.logger = logging.getLogger(f'TerminalInputSensor-{self.name}')

    async def start(self):
        """
        Starts the sensor by launching the input thread.
        """
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        # self.logger.info(f"{self.name} started.")

    async def stop(self):
        """
        Stops the sensor by signaling the thread to stop and waiting for it to finish.
        """
        self._running = False
        if self._thread:
            self._thread.join()
            # self.logger.info(f"{self.name} stopped.")

    def _run(self):
        """
        The main loop that reads user input and emits events.
        """
        loop = self.event_bus.loop
        if loop is None:
            # self.logger.error("EventBus loop is not set. Cannot emit events.")
            return

        while self._running:
            try:
                user_input = input(self.prompt_message)
                if not self._running:
                    break  # Exit if stopped during input

                # # Process input into stimuli
                # stimuli = self.signal_to_stimuli(user_input)
                
                # Emit the stimuli as an event
                asyncio.run_coroutine_threadsafe(
                    self.event_bus.emit('perception.stimuli', payload=user_input),  # TODO: rename event later
                    loop
                )
            except EOFError:
                # Handle end of input (Ctrl+D)
                # self.logger.info("EOF received. Stopping TerminalInputSensor.")
                self._running = False
            except KeyboardInterrupt:
                # Handle Ctrl+C
                # self.logger.info("KeyboardInterrupt received. Stopping TerminalInputSensor.")
                self._running = False
            except Exception as e:
                # self.logger.error(f"Error in TerminalInputSensor: {e}")
                self._running = False