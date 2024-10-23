import time
from datetime import datetime

from airtrafficsim.core.environment import Environment

class RealTimeEnvironment(Environment):
    def __init__(self, file_name, time_delta=1, weather_mode="ISA", performance_mode="BADA"):
        # Absurdly high end time to avoid simulation ending prematurely
        # TODO: Eventually support None end_time to run forever
        super().__init__(file_name, start_time=datetime.now(), end_time=24 * 3600, weather_mode=weather_mode, performance_mode=performance_mode)

        self.time_delta = time_delta

        self.socketio = None

    def handle_command(self, aircraft, command, payload):
        pass

    def run(self, socketio=None):
        """
        Run the simulation for all timesteps.

        Parameters
        ----------
        socketio : socketio object, optional
            Socketio object to handle communciation when running simulation, by default None
        """
        if socketio:
            socketio.emit('simulationEnvironment', {
                          'header': self.header, 'file': self.file_name})

            @socketio.on('command')
            def handle_command_message(command):
                # Command: { aircraft: str, command: str, payload: any }
                # Command types:
                # - takeoff
                # - heading
                # - altitude
                # - airspeed
                # - resume_nav
                # - flight_plan
                # - approach

                print('received command', command)

                return self.handle_command(command['aircraft'], command['command'], command['payload'] if 'payload' in command else None)

        self.socketio = socketio

        delay = self.time_delta
        next_time = time.time() + delay
        while True:
            time.sleep(max(0, next_time - time.time()))

            if self.should_end():
                self.end_time = self.global_time
                break

            self.step(socketio)
            next_time += (time.time() - next_time) // delay * delay + delay

        print("")
        print("Simulation finished")
