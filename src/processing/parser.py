import re
from src.processing.models import Station, WeatherRecord
from src.utils.logger import config_logger

# Inicializamos el logger para registrar el proceso de limpieza
logger = config_logger(__name__)

class DataParser:
    def __init__(self, allowed_stations):
        """
        Allowed stations: [{'nombre': 'Retiro', 'id': '3195'}, ...]
        """
        self.station_mapping = {s['id']: s['nombre'] for s in allowed_stations}

    def parse_and_clean(self, raw_data):
        """
        Recibe la lista de la API y devuelve una lista de objetos WeatherRecord.
        """
        processed_data = []
        seen_indicators = set()  # Para evitar duplicados en la misma carga

        for register in raw_data:
            indicator = register.get("indicativo")
            
            # Filtro de estaciones permitidas y control de duplicados
            if indicator in self.station_mapping and indicator not in seen_indicators:
                try:
                    def clean_float(value):
                        if value is None: return None
                        try:
                            return float(str(value).replace(',', '.'))
                        except (ValueError, TypeError):
                            return None

                    # Creamos el objeto WeatherRecord con los datos mapeados
                    record = WeatherRecord(
                        date=register.get("fecha"),
                        station_id=indicator,
                        name=self.station_mapping[indicator],
                        province=register.get("provincia"),
                        temp_avg=clean_float(register.get("tmed")),
                        temp_min=clean_float(register.get("tmin")),
                        time_temp_min=register.get("horatmin"),
                        temp_max=clean_float(register.get("tmax")),
                        time_temp_max=register.get("horatmax"),
                        humidity_avg=clean_float(register.get("hrMedia")),
                        humidity_min=clean_float(register.get("hrMin")),
                        humidity_max=clean_float(register.get("hrMax")),
                        time_humidity_min=register.get("horahrmin"),
                        time_humidity_max=register.get("horahrmax"),
                        precipitation=clean_float(register.get("prec")),
                        wind_gust=clean_float(register.get("racha")),
                        time_wind_gust=register.get("horaracha"),
                        wind_direction=clean_float(register.get("dir")),
                        wind_speed_avg=clean_float(register.get("velmedia"))
                    )
                    
                    # Validación mínima para alertas
                    if record.temp_max is not None and record.wind_gust is not None:
                        processed_data.append(record)
                        seen_indicators.add(indicator)
                    else:
                        logger.warning(f"Datos esenciales (temp/viento) ausentes en {record.name} - Omitido.")
                        
                except Exception as e:
                    logger.error(f"Error inesperado procesando la estación {indicator}: {e}")
        
        logger.info(f"Procesados {len(processed_data)} objetos WeatherRecord de Madrid.")
        return processed_data

    def parse_stations(self, raw_data, filter_city="MADRID"):
        """
        Crea un mapa de objetos Station filtrando por ciudad.
        """
        stations_map = {}
        
        for item in raw_data:
            name = item.get("nombre")
            indicativo = item.get("indicativo")

            if indicativo and name and re.split(r'[,\s]+', name)[0] == filter_city:
                try:
                    station_obj = Station(
                        indicativo=indicativo,
                        nombre=name,
                        provincia=item.get("provincia"),
                        latitud=item.get("latitud"),
                        longitud=item.get("longitud"),
                        altitud=item.get("altitud")
                    )
                    stations_map[indicativo] = station_obj
                except Exception as e:
                    logger.error(f"Error al crear objeto Station para {indicativo}: {e}")
                    
        return stations_map