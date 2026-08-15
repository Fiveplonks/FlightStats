from dataclasses import dataclass
from datetime import date, time
from typing import Optional


@dataclass
class Flight:
    date: date
    departure: str
    departure_time: Optional[time]
    arrival: str
    arrival_time: Optional[time]
    aircraft: str
    registration: str
    flight_minutes: Optional[int]
    logged_flight_minutes: Optional[int] = None
    logged_time_status: str = "missing"
