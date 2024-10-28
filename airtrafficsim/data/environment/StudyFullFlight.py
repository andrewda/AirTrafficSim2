import numpy as np
import time

from datetime import datetime
from pathlib import Path

from airtrafficsim.core.realtime_environment import RealTimeEnvironment
from airtrafficsim.core.aircraft import Aircraft
from airtrafficsim.core.navigation import Nav
from airtrafficsim.utils.enums import Config, FlightPhase


def extract_number(string):
    digits = [char for char in string if char.isdigit()]
    if digits:
        return int(''.join(digits))
    return None

class StudyFullFlight(RealTimeEnvironment):

    def __init__(self):
        # Initialize environment super class
        super().__init__(file_name=Path(__file__).name.removesuffix('.py'),  # File name (do not change)
                         weather_mode="",
                         performance_mode="BADA"
                        )

        self.aircraft = {}

        # Add aircraft
        # lat_dep, long_dep, alt_dep = Nav.get_runway_coord("KPDX", "28L")

        # self.aircraft['HMT 110'] = Aircraft(self.traffic, call_sign="HMT 110", aircraft_type="A320", flight_phase=FlightPhase.TAKEOFF, configuration=Config.TAKEOFF,
        #                               lat=lat_dep, long=long_dep, alt=alt_dep, heading=280.0, cas=149.0,
        #                               fuel_weight=5273.0, payload_weight=12000.0,
        #                               departure_airport="KPDX", departure_runway="RW28L", sid="",
        #                               arrival_airport="KSLE", arrival_runway="13", star="", approach="R13",
        #                               flight_plan=["YIBPU", "UBG"],
        #                               cruise_alt=18000)


    def should_end(self):

        # Check for aircraft landing and remove
        for callsign in self.traffic.call_sign:
            index = np.where(self.traffic.call_sign == callsign)[0][0]
            if self.aircraft[callsign].get_next_wp() is None:
                # index = np.where(self.traffic.call_sign == callsign)[0][0]
                # self.traffic.del_aircraft(self.traffic.index[index])
                self.aircraft[callsign].set_flight_phase(FlightPhase.TAXI_DEST)
                self.last_sent_time = 0
                # del self.aircraft[callsign]

        return super().should_end()

    def atc_command(self):
        # User algorithm
        pass

        # if self.global_time == 30:
        #     lat_dep, long_dep, alt_dep = Nav.get_runway_coord("KPDX", "28L")

        #     self.aircraft['HMT 120'] = Aircraft(self.traffic, call_sign="HMT 120", aircraft_type="A320", flight_phase=FlightPhase.TAKEOFF, configuration=Config.TAKEOFF,
        #                               lat=lat_dep, long=long_dep, alt=alt_dep, heading=280.0, cas=149.0,
        #                               fuel_weight=5273.0, payload_weight=12000.0,
        #                               departure_airport="KPDX", departure_runway="RW28L", sid="",
        #                               arrival_airport="KSLE", arrival_runway="13", star="", approach="R13",
        #                               flight_plan=["YIBPU", "UBG"],
        #                               cruise_alt=18000)

    def handle_command(self, aircraft, command, payload):
        print(f'received command {command} for aircraft {aircraft} with payload {payload}')

        if command == "init":
            for aircraft_config in payload:
                callsign = aircraft_config['callsign']
                print(aircraft_config['departure_airport'], aircraft_config['departure_runway'][2:])
                lat_dep, long_dep, alt_dep = Nav.get_runway_coord(aircraft_config['departure_airport'], aircraft_config['departure_runway'][2:])

                default_config = {
                    # "call_sign": callsign,
                    "aircraft_type": "C208",
                    "flight_phase": FlightPhase.TAXI_ORIGIN,
                    "configuration": Config.TAKEOFF,
                    "lat": lat_dep,
                    "long": long_dep,
                    "alt": alt_dep,
                    "heading": extract_number(aircraft_config['departure_runway']) * 100,
                    "cas": 80.0,
                    "fuel_weight": 900,
                    "payload_weight": 0.0,
                    "cruise_alt": 18000,
                    "sid": "",
                    "star": "",
                }

                self.aircraft[callsign] = Aircraft(self.traffic, **default_config, **aircraft_config)


        elif command == "takeoff":
            self.aircraft[aircraft].set_flight_phase(FlightPhase.TAKEOFF)

        elif command == "heading":
            self.aircraft[aircraft].set_heading(payload)

        elif command == "altitude":
            self.aircraft[aircraft].set_alt(payload)
            self.aircraft[aircraft].set_vs(500 if payload >= self.aircraft[aircraft].get_alt() else -500)

        elif command == "resume_nav":
            self.aircraft[aircraft].resume_own_navigation()

        elif command == "flight_plan":
            self.aircraft[aircraft].set_flight_plan(**payload)

        elif command == "delete":
            index = np.where(self.traffic.call_sign == aircraft)[0][0]
            self.traffic.del_aircraft(self.traffic.index[index])
            del self.aircraft[aircraft]

        return True
