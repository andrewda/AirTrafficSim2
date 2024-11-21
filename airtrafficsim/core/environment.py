import time
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import csv
from pathlib import Path

from airtrafficsim.utils.unit_conversion import Unit
from airtrafficsim.utils.enums import FlightPhase, Config, SpeedMode, VerticalMode, APSpeedMode, APThrottleMode, APVerticalMode, APLateralMode
from airtrafficsim.core.traffic import Traffic


class Environment:
    """
    Base class for simulation environment

    """

    def __init__(self, file_name, start_time, end_time, weather_mode="ISA", performance_mode="BADA", create_log_file=True):
        # User setting
        self.start_time = start_time
        """The simulation start time [datetime object]"""
        self.end_time = end_time
        """The simulation end time [s]"""

        # Simulation variable
        self.traffic = Traffic(file_name, start_time,
                               end_time, weather_mode, performance_mode)
        self.global_time = 0                    # [s]

        # Handle io
        self.datetime = datetime.now(timezone.utc)
        self.last_sent_time = time.time()
        self.graph_type = 'None'
        self.packet_id = 0
        self.buffer_data = []

        self.paused = False
        self.stopped = False

        self.weather = None

        if create_log_file:
            self.create_log_files(file_name)


    def create_log_files(self, directory_name):
        self.file_name = datetime.now().isoformat(timespec='seconds') + '-' + directory_name
        self.folder_path = Path(__file__).parent.parent.resolve().joinpath('data/result/' + self.file_name)
        self.folder_path.mkdir()

        if 'sim_file' in self.__dict__:
            self.sim_file.close()

        self.sim_file_path = self.folder_path.joinpath('simulation.csv')
        self.sim_file = open(self.sim_file_path, 'w+')
        self.sim_writer = csv.writer(self.sim_file)

        self.sim_header = ['timestamp', 'id', 'callsign', 'lat', 'long', 'alt',
                       'cas', 'tas', 'vs', 'heading', 'bank_angle', 'path_angle',
                       'ap_track_angle', 'ap_heading', 'ap_alt', 'ap_cas', 'ap_procedural_speed',
                       'ap_wp_index', 'ap_next_wp', 'ap_dist_to_next_fix',
                       'flight_phase', 'configuration', 'speed_mode', 'vertical_mode', 'ap_speed_mode', 'ap_lateral_mode', 'ap_throttle_mode']
        self.sim_writer.writerow(self.sim_header)

    def atc_command(self):
        """
        Virtual method to execute user command each timestep.
        """
        pass

    def should_end(self):
        """
        Virtual method to determine whether the simulation should end each timestep.
        """
        return self.stopped

    def is_paused(self):
        return self.paused

    def step(self, socketio=None):
        """
        Conduct one simulation timestep.
        """
        start_time = time.time()

        if not self.is_paused():
            # Run atc command
            self.atc_command()
            # Run update loop
            self.traffic.update(self.global_time)
            # Save to file
            self.save()

        # print("Environment - step() for global time", self.global_time,
        #       "/", self.end_time, "finished at", time.time() - start_time)

        if socketio != None:
            # Save to buffer
            data = np.column_stack((self.traffic.index,
                                    self.traffic.call_sign,
                                    np.full(len(self.traffic.index), (self.start_time + timedelta(
                                        seconds=self.global_time)).isoformat(timespec='seconds')),
                                    self.traffic.long,
                                    self.traffic.lat,
                                    Unit.ft2m(self.traffic.alt),
                                    self.traffic.cas))
            self.buffer_data.extend(data)

            @socketio.on('setSimulationGraphType')
            def set_simulation_graph_type(graph_type):
                self.graph_type = graph_type

            now = time.time()
            if ((now - self.last_sent_time) > 0.5) or (self.global_time == self.end_time):
                self.send_to_client(socketio)
                socketio.sleep(0)
                self.last_sent_time = now
                self.buffer_data = []

        if not self.is_paused():
            self.global_time += 1

    def run(self, socketio=None):
        """
        Run the simulation for all timesteps.

        Parameters
        ----------
        socketio : socketio object, optional
            Socketio object to handle communciation when running simulation, by default None
        """
        for _ in range(self.end_time+1):
            # One timestep

            # Check if the simulation should end
            if self.should_end():
                self.end_time = self.global_time
                break

            self.step(socketio)

        # print("")
        # print("Export to CSVs")
        # self.export_to_csv()
        print("")
        print("Simulation finished")

    def stop(self):
        self.stopped = True

    def save(self):
        """
        Save all states variable of one timestemp to csv file.
        """
        if 'sim_writer' not in self.__dict__:
            return

        current_time = datetime.now().isoformat()

        data = np.column_stack(([current_time for i in self.traffic.index], self.traffic.index, self.traffic.call_sign, self.traffic.lat, self.traffic.long, self.traffic.alt,
                                self.traffic.cas, self.traffic.tas, self.traffic.vs,
                                self.traffic.heading, self.traffic.bank_angle, self.traffic.path_angle,
                                self.traffic.ap.track_angle, self.traffic.ap.heading, self.traffic.ap.alt, self.traffic.ap.cas, self.traffic.ap.procedure_speed,
                                self.traffic.ap.flight_plan_index, [self.traffic.ap.flight_plan_name[i][val] if (val < len(self.traffic.ap.flight_plan_name[i])) else "NONE" for i, val in enumerate(
                                    self.traffic.ap.flight_plan_index)], self.traffic.ap.dist, self.traffic.ap.holding_round,  # autopilot variable
                                [FlightPhase(i).name for i in self.traffic.flight_phase], [Config(i).name for i in self.traffic.configuration], [
            SpeedMode(i).name for i in self.traffic.speed_mode], [VerticalMode(i).name for i in self.traffic.vertical_mode],
            [APSpeedMode(i).name for i in self.traffic.ap.speed_mode], [APLateralMode(i).name for i in self.traffic.ap.lateral_mode], [APThrottleMode(i).name for i in self.traffic.ap.auto_throttle_mode]))  # mode

        self.sim_writer.writerows(data)
        self.sim_file.flush()

    def export_to_csv(self):
        """
        Export the simulation result to a csv file.
        """
        df = pd.read_csv(self.sim_file_path)
        for id in df['id'].unique():
            df[df['id'] == id].to_csv(
                self.folder_path.joinpath(str(id)+'.csv'), index=False)
        # self.file_path.unlink()

    def send_to_client(self, socketio):
        """
        Send the simulation data to client.

        Parameters
        ----------
        socketio : socketio object
            socketio object to handle communciation when running simulation
        """

        # Additional aircraft telemetry
        # TODO: emit at a slower rate? probably not necessary for now
        aircraft_data = [
            {
                'callsign': self.traffic.call_sign[i].item(),
                'aircraftType': self.traffic.aircraft_type[i].item(),
                'flightPhase': self.traffic.flight_phase[i].item(),
                'configuration': self.traffic.configuration[i].item(),
                'lateralMode': self.traffic.ap.lateral_mode[i].item(),
                'verticalMode': self.traffic.vertical_mode[i].item(),
                'position': [self.traffic.lat[i].item(), self.traffic.long[i].item()],
                'altitude': self.traffic.alt[i].item(),
                'heading': self.traffic.heading[i].item(),
                'track': self.traffic.track_angle[i].item(),
                'tas': 0 if self.traffic.flight_phase[i].item() == FlightPhase.TAXI_ORIGIN or self.traffic.flight_phase[i].item() == FlightPhase.TAXI_DEST else self.traffic.tas[i].item(),
                'vs': 0 if self.traffic.flight_phase[i].item() == FlightPhase.TAXI_ORIGIN or self.traffic.flight_phase[i].item() == FlightPhase.TAXI_DEST else self.traffic.vs[i].item(),
                'flightPlan': self.traffic.ap.flight_plan_name[i],
                'flightPlanEnroute': self.traffic.ap.flight_plan_enroute[i],
                'flightPlanPos': list(zip(self.traffic.ap.flight_plan_lat[i], self.traffic.ap.flight_plan_long[i])),
                'flightPlanTargetSpeed': self.traffic.ap.flight_plan_target_speed[i],
                'flightPlanIndex': self.traffic.ap.flight_plan_index[i].item(),
                'dist': self.traffic.ap.dist[i],
                'departureAirport': self.traffic.ap.departure_airport[i],
                'departureRunway': self.traffic.ap.departure_runway[i],
                'sid': self.traffic.ap.sid[i],
                'arrivalAirport': self.traffic.ap.arrival_airport[i],
                'arrivalRunway': self.traffic.ap.arrival_runway[i],
                'star': self.traffic.ap.star[i],
                'approach': self.traffic.ap.approach[i],
                'frequency': self.traffic.frequency[i],
            }
            for i in range(len(self.traffic.index))
        ]

        socketio.emit('simulationData', {
            'packet_id': self.packet_id,
            'global_time': self.global_time,
            'aircraft': aircraft_data,
            'weather': self.weather,
            'paused': self.paused
        })

        self.packet_id = self.packet_id + 1
