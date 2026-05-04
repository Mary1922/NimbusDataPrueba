import re
from typing import List, Dict, Any, Optional
from src.processing.models import Station, WeatherRecord
import logging

# Initialize logger for tracking parsing and cleaning operations
logger = logging.getLogger(__name__)

class DataParser:
    def __init__(self):
        """
        Allowed stations: [{'nombre': 'Retiro', 'id': '3195'}, ...]
        """
        pass
    
    @staticmethod
    def _to_iso8601_format(date_str):
        """
        Normalizes various date strings to a consistent ISO8601-like format.
        Example: '2026-05-02' -> '2026-05-02T00:00:00UTC'
        """
        # Remove any timezone offsets like +0200
        clean_date = date_str.split('+')[0]

        # Case: Simple date without time component
        if 'T' not in clean_date:
            return f"{clean_date}T00:00:00UTC"
        
        # Case: Date has time but missing UTC suffix
        if not clean_date.endswith("UTC"):
            return f"{clean_date}UTC"
            
        return clean_date

    @staticmethod
    def _clean_float(value: Any) -> Optional[float]:
        """
        Safely converts mixed-type inputs (string with commas, ints) to floats.
        Returns None if conversion fails.
        """
        if value is None: return None
        try:
            return float(str(value).replace(',', '.'))
        except (ValueError, TypeError):
            return None

    def parse_daily_weather(self, raw_data: List[Dict[str, Any]]) -> List[WeatherRecord]:
        """
        Parses a list of daily weather summaries from the API into WeatherRecord objects.
        
        Args:
            raw_data: List of dictionaries directly from AEMET daily endpoints.
        Returns:
            A list of successfully parsed WeatherRecord instances.
        """
        processed_data = [] 
        for register in raw_data:
            indicator = register.get("indicativo")
            
            try:
                # Mapping AEMET keys to standardized WeatherRecord attributes
                record = WeatherRecord(
                    date=self._to_iso8601_format(register.get("fecha")),
                    station_id=indicator,
                    name=register.get("nombre"),
                    #province=register.get("provincia"),
                    temp_avg=self._clean_float(register.get("tmed")),
                    temp_min=self._clean_float(register.get("tmin")),
                    #time_temp_min=register.get("horatmin"),
                    temp_max=self._clean_float(register.get("tmax")),
                    #time_temp_max=register.get("horatmax"),
                    humidity_avg=self._clean_float(register.get("hrMedia")),
                    #humidity_min=self.clean_float(register.get("hrMin")),
                    #humidity_max=self.clean_float(register.get("hrMax")),
                    #time_humidity_min=register.get("horahrmin"),
                    #time_humidity_max=register.get("horahrmax"),
                    precipitation=self._clean_float(register.get("prec")),
                    #wind_gust=self.clean_float(register.get("racha")),
                    #time_wind_gust=register.get("horaracha"),
                    wind_direction=self._clean_float(register.get("dir")),
                    wind_speed_avg=self._clean_float(register.get("velmedia"))
                )     
                processed_data.append(record)

            except Exception as e:
                logger.error(f"Error inesperado procesando la estación {indicator}: {e}")
        
        logger.info(f"Procesados {len(processed_data)} objetos WeatherRecord de Madrid.")
        return processed_data
    
    def parse_hourly_weather(self, raw_data: list[dict]) -> list[WeatherRecord]:
        """
        Selects and parses the most recent entry from an hourly data stream.
        This is used for real-time monitoring where the last entry represents the current state.
        """
        if not raw_data:
            return []

        # Sort by 'fint' (observation end time) to guarantee the latest data is selected
        try:
            raw_data.sort(key=lambda x: x.get("fint", ""))
            latest_record = raw_data[-1]
            
            # Map hourly-specific keys (ta, hr, vv) to standard model fields
            record_obj = WeatherRecord(
                date=self._to_iso8601_format(latest_record.get("fint")),
                station_id=latest_record.get("idema"),
                name=latest_record.get("ubi"),
                temp_avg=self._clean_float(latest_record.get("ta")),
                temp_min=self._clean_float(latest_record.get("tmin")),
                temp_max=self._clean_float(latest_record.get("tmax")),
                humidity_avg=self._clean_float(latest_record.get("hr")),
                precipitation=self._clean_float(latest_record.get("prec")),
                wind_direction=self._clean_float(latest_record.get("dv")),
                wind_speed_avg=self._clean_float(latest_record.get("vv"))
            )
            return [record_obj]

        except Exception as e:
            logger.error("Error al identificar el registro más reciente "
                         f"de hoy para la estacion : {e}")
            return []
    
    def parse_stations(self, raw_data: List[Dict[str, Any]], 
                       filter_city: str = "MADRID") -> Dict[str, Station]:
        """
        Converts raw station metadata into a dictionary of Station objects,
        filtered by a specific city/region prefix.
        
        Args:
            raw_data: List of all available stations from AEMET.
            filter_city: Target city prefix (e.g., 'MADRID').
        Returns:
            Dictionary mapping station_id to Station objects.
        """
        stations_map = {}
        
        for item in raw_data:
            name = item.get("nombre", "")
            station_id = item.get("indicativo")

            # Check if station name starts with the target city (e.g., "MADRID, RETIRO")
            if station_id and name and re.split(r'[,\s]+', name)[0].upper() == filter_city:
                try:
                    station_obj = Station(
                        station_id=station_id,
                        name=name,
                        province=item.get("provincia"),
                        latitude=item.get("latitud"),
                        longitude=item.get("longitud"),
                        altitude=item.get("altitud")
                    )
                    stations_map[station_id] = station_obj

                except Exception as e:
                    logger.error(f"Error al crear objeto Station para {station_id}: {e}")
                    
        return stations_map