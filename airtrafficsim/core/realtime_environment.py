import time
import csv
import threading
from datetime import datetime

from airtrafficsim.core.environment import Environment

class RealTimeEnvironment(Environment):
    def __init__(self, file_name, time_delta=1, weather_mode="ISA", performance_mode="BADA"):
        # Absurdly high end time to avoid simulation ending prematurely
        # TODO: Eventually support None end_time to run forever
        super().__init__(file_name, start_time=datetime.now(), end_time=24 * 3600, weather_mode=weather_mode, performance_mode=performance_mode, create_log_file=False)

        self.time_delta = time_delta

        self.socketio = None

    def create_log_files(self, directory_name):
        super().create_log_files(directory_name)

        if 'cmd_file' in self.__dict__:
            self.cmd_file.close()

        self.cmd_file_path = self.folder_path.joinpath('commands.csv')
        self.cmd_file = open(self.cmd_file_path, 'w+')
        self.cmd_writer = csv.writer(self.cmd_file)

        self.cmd_header = ['timestamp', 'aircraft', 'command', 'payload']
        self.cmd_writer.writerow(self.cmd_header)

    def handle_command(self, aircraft, command, payload):
        if command == "init":
            if "name" in payload:
                self.create_log_files(payload['name'])

        pass

    def loop(self, socketio):
        delay = self.time_delta
        next_time = time.time() + delay
        while True:
            socketio.sleep(max(0, next_time - time.time()))

            if self.should_end():
                self.end_time = self.global_time
                break

            self.step(socketio)
            next_time += (time.time() - next_time) // delay * delay + delay

    def run(self, socketio=None):
        """
        Run the simulation for all timesteps.

        Parameters
        ----------
        socketio : socketio object, optional
            Socketio object to handle communciation when running simulation, by default None
        """
        if socketio:
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

                receive_time = datetime.now()

                res = self.handle_command(command['aircraft'], command['command'], command['payload'] if 'payload' in command else None)

                self.cmd_writer.writerow([receive_time.isoformat(), command['aircraft'], command['command'], command['payload'] if 'payload' in command else ''])
                self.cmd_file.flush()

                return res

        self.socketio = socketio

        socketio.start_background_task(self.loop, socketio).join()

        print("")
        print("Simulation finished")
