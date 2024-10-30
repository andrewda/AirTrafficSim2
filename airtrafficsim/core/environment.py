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

    def __init__(self, file_name, start_time, end_time, weather_mode="ISA", performance_mode="BADA"):
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

        self.stopped = False

        self.weather = None

        # File IO
        self.file_name = file_name+'-' + \
            self.datetime.isoformat(timespec='seconds')
        self.folder_path = Path(__file__).parent.parent.resolve().joinpath(
            'data/result/'+self.file_name)
        self.folder_path.mkdir()
        self.file_path = self.folder_path.joinpath(self.file_name+'.csv')
        self.writer = csv.writer(open(self.file_path, 'w+'))
        self.header = ['timestep', 'timestamp', 'id', 'callsign', 'lat', 'long', 'alt',
                       'cas', 'tas', 'mach', 'vs',
                       'heading', 'bank_angle', 'path_angle',
                       'mass', 'fuel_consumed',
                       'thrust', 'drag', 'esf', 'accel',
                       'ap_track_angle', 'ap_heading', 'ap_alt', 'ap_cas', 'ap_mach', 'ap_procedural_speed',
                       'ap_wp_index', 'ap_next_wp', 'ap_dist_to_next_fix', 'ap_holding_round',
                       'flight_phase', 'configuration', 'speed_mode', 'vertical_mode', 'ap_speed_mode', 'ap_lateral_mode', 'ap_throttle_mode']
        self.writer.writerow(self.header)
        self.header.remove('timestep')
        self.header.remove('timestamp')
        self.header.remove('id')
        self.header.remove('callsign')

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

    def step(self, socketio=None):
        """
        Conduct one simulation timestep.
        """
        start_time = time.time()

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

        self.global_time += 1

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
        pass
        # data = np.column_stack((np.full(len(self.traffic.index), self.global_time), np.full(len(self.traffic.index), (self.start_time + timedelta(seconds=self.global_time)).isoformat(timespec='seconds')), self.traffic.index, self.traffic.call_sign, self.traffic.lat, self.traffic.long, self.traffic.alt,
        #                         self.traffic.cas, self.traffic.tas, self.traffic.mach, self.traffic.vs,
        #                         self.traffic.heading, self.traffic.bank_angle, self.traffic.path_angle,
        #                         self.traffic.mass, self.traffic.fuel_consumed,
        #                         self.traffic.perf.thrust, self.traffic.perf.drag, self.traffic.perf.esf, self.traffic.accel,
        #                         self.traffic.ap.track_angle, self.traffic.ap.heading, self.traffic.ap.alt, self.traffic.ap.cas, self.traffic.ap.mach, self.traffic.ap.procedure_speed,
        #                         self.traffic.ap.flight_plan_index, [self.traffic.ap.flight_plan_name[i][val] if (val < len(self.traffic.ap.flight_plan_name[i])) else "NONE" for i, val in enumerate(
        #                             self.traffic.ap.flight_plan_index)], self.traffic.ap.dist, self.traffic.ap.holding_round,  # autopilot variable
        #                         [FlightPhase(i).name for i in self.traffic.flight_phase], [Config(i).name for i in self.traffic.configuration], [
        #     SpeedMode(i).name for i in self.traffic.speed_mode], [VerticalMode(i).name for i in self.traffic.vertical_mode],
        #     [APSpeedMode(i).name for i in self.traffic.ap.speed_mode], [APLateralMode(i).name for i in self.traffic.ap.lateral_mode], [APThrottleMode(i).name for i in self.traffic.ap.auto_throttle_mode]))  # mode

        # self.writer.writerows(data)

    def export_to_csv(self):
        """
        Export the simulation result to a csv file.
        """
        df = pd.read_csv(self.file_path)
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
        document = [{
            "id": "document",
            "name": "simulation",
            "version": "1.0",
            "clock": {
                "interval": self.start_time.isoformat()+"/"+(self.start_time + timedelta(seconds=self.end_time)).isoformat(),
                "currentTime": (datetime.now() - timedelta(seconds=3)).isoformat(),
            }
        }]

        df_buffer = pd.DataFrame(self.buffer_data)
        if self.buffer_data:
            for id in df_buffer.iloc[:, 0].unique():
                content = df_buffer[df_buffer.iloc[:, 0] == id]

                call_sign = content.iloc[0, 1]
                positions = content.iloc[:, [2, 3, 4, 5]
                                         ].to_numpy().flatten().tolist()
                label = [{"interval": time+"/"+(self.start_time + timedelta(seconds=self.end_time)).isoformat(),
                          "string": call_sign+"\n"+str(np.floor(Unit.m2ft(alt)))+"ft "+str(np.floor(cas))+"kt"}
                         for time, alt, cas in zip(content.iloc[:, 2].to_numpy(), content.iloc[:, 5].to_numpy(dtype=float), content.iloc[:, 6].to_numpy(dtype=float))]

                trajectory = {
                    "id": call_sign,
                    "position": {
                        "cartographicDegrees": positions
                    },
                    "point": {
                        "pixelSize": 10,
                        "color": {
                            "rgba": [39, 245, 106, 215]
                        }
                    },
                    "path": {
                        "leadTime": 0,
                        "trailTime": 30,
                        "distanceDisplayCondition": {
                            "distanceDisplayCondition": [0, 1500000]
                        }
                    },
                    "label": {
                        "text": label,
                        "font": "9px sans-serif",
                        "horizontalOrigin": "LEFT",
                        "pixelOffset": {
                                "cartesian2": [20, 20],
                        },
                        "distanceDisplayCondition": {
                            "distanceDisplayCondition": [0, 1500000]
                        },
                        "showBackground": "false",
                        "backgroundColor": {
                            "rgba": [0, 0, 0, 50]
                        }
                    }
                }
                document.append(trajectory)

        graph_data = []
        if self.graph_type != 'None':
            df = pd.read_csv(self.file_path)
            for id in df['id'].unique():
                content = df[df['id'] == id]
                graph_data.append({
                    "x": content['timestep'].to_list(),
                    "y": content[self.graph_type].to_list(),
                    "name": content.iloc[0]['callsign'],
                    "type": 'scattergl',
                    "mode": 'lines',
                })

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
                'departureAirport': self.traffic.ap.departure_airport[i],
                'departureRunway': self.traffic.ap.departure_runway[i],
                'sid': self.traffic.ap.sid[i],
                'arrivalAirport': self.traffic.ap.arrival_airport[i],
                'arrivalRunway': self.traffic.ap.arrival_runway[i],
                'star': self.traffic.ap.star[i],
                'approach': self.traffic.ap.approach[i],
            }
            for i in range(len(self.traffic.index))
        ]

        socketio.emit('simulationData', {'czml': document, 'progress': self.global_time /
                      self.end_time, 'packet_id': self.packet_id, 'graph': graph_data,
                      'aircraft': aircraft_data, 'weather': self.weather})
        self.packet_id = self.packet_id + 1
