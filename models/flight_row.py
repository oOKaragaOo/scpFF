from dataclasses import dataclass

@dataclass
class FlightRow:
    airport: str
    date: str
    type: str
    flight_number: str = ""
    airline: str = ""
    origin: str = ""
    destination: str = ""
    time: str = ""
