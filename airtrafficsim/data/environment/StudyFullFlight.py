import numpy as np
import time

from datetime import datetime
from pathlib import Path

from airtrafficsim.core.realtime_environment import RealTimeEnvironment
from airtrafficsim.core.aircraft import Aircraft
from airtrafficsim.core.navigation import Nav
from airtrafficsim.utils.enums import Config, FlightPhase


aircraft_config = {
    'HMT 110': {
        "heading": 283.0, "cas": 149.0,
        "departure_airport": "KPDX", "departure_runway": "RW28L", "sid": "",
        "arrival_airport": "KSLE", "arrival_runway": "13", "star": "", "approach": "R13",
        "flight_plan": ["YIBPU", "UBG"],
    },
    'HMT 120': {
        "heading": 283.0, "cas": 149.0,
        "departure_airport": "KPDX", "departure_runway": "RW28L", "sid": "",
        "arrival_airport": "KCVO", "arrival_runway": "17", "star": "", "approach": "R17",
        "flight_plan": ["YIBPU", "ADLOW"],
    }
}


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

            print(callsign, self.aircraft[callsign].get_alt(), self.aircraft[callsign].get_next_wp(), self.traffic.ap.flight_plan_index[index])
            # if (callsign == 'HMT 110' and self.global_time == 60) or (callsign == 'HMT 120' and self.global_time == 90):
            if self.aircraft[callsign].get_next_wp() is None:
            # if self.aircraft[callsign].get_alt() == 0:
                index = np.where(self.traffic.call_sign == callsign)[0][0]
                self.traffic.del_aircraft(self.traffic.index[index])
                self.last_sent_time = 0

        return False

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

        if command == "takeoff":
            if aircraft in self.aircraft:
                print(f'{aircraft} already in aircraft list')
                return

            print(aircraft_config[aircraft], aircraft_config[aircraft]['departure_airport'], aircraft_config[aircraft]['departure_runway'][2:])
            lat_dep, long_dep, alt_dep = Nav.get_runway_coord(aircraft_config[aircraft]['departure_airport'], aircraft_config[aircraft]['departure_runway'][2:])


            # TODO: move all this to client config, maybe with default values here
            self.aircraft[aircraft] = Aircraft(self.traffic, call_sign=aircraft, aircraft_type="C208", flight_phase=FlightPhase.TAKEOFF, configuration=Config.TAKEOFF,
                                                lat=lat_dep, long=long_dep, alt=alt_dep, heading=aircraft_config[aircraft]['heading'], cas=aircraft_config[aircraft]['cas'],
                                                # fuel_weight=5273.0, payload_weight=12000.0,
                                                fuel_weight=900, payload_weight=0.0,
                                                departure_airport=aircraft_config[aircraft]['departure_airport'], departure_runway=aircraft_config[aircraft]['departure_runway'], sid=aircraft_config[aircraft]['sid'],
                                                arrival_airport=aircraft_config[aircraft]['arrival_airport'], arrival_runway=aircraft_config[aircraft]['arrival_runway'], star=aircraft_config[aircraft]['star'], approach=aircraft_config[aircraft]['approach'],
                                                flight_plan=aircraft_config[aircraft]['flight_plan'],
                                                cruise_alt=18000)

        elif command == "heading":
            self.aircraft[aircraft].set_heading(payload)

        elif command == "altitude":
            self.aircraft[aircraft].set_alt(payload)

        # elif command == "airspeed":
        #     self.aircraft[aircraft].set_cas(payload)

        elif command == "resume_nav":
            self.aircraft[aircraft].resume_own_navigation()

        elif command == "flight_plan":
            self.aircraft[aircraft].set_flight_plan(**payload)

        return True
