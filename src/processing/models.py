from dataclasses import dataclass
from typing import Optional

@dataclass
class Station:
    station_id: str
    name: str
    province: str
    latitude: str
    longitude: str
    altitude: str
    # state: str = "active"
    # registration_date: Optional[str] = None

    @property
    def geo_id(self) -> str:
        return f"{self.station_id}_{self.latitude}_{self.longitude}_{self.altitude}"

@dataclass
class WeatherRecord:
    date: str
    station_id: str
    name: str
    province: str
    temp_avg: float
    temp_min: float
    time_temp_min: Optional[str] = None
    temp_max: float
    time_temp_max: Optional[str] = None
    humidity_avg: Optional[int] = None
    humidity_min: Optional[int] = None
    humidity_max: Optional[int] = None
    time_humidity_min: Optional[str] = None
    time_humidity_max: Optional[str] = None
    precipitation: Optional[float] = None
    wind_gust: Optional[float] = None
    time_wind_gust: Optional[str] = None
    wind_direction: Optional[float] = None
    wind_speed_avg: Optional[float] = None