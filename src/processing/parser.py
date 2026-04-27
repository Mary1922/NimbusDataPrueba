from utils.logger import config_logger

# Inicializamos el logger para registrar el proceso de limpieza
logger = config_logger()

class DataParser:
    def __init__(self, allowed_stations):
        """
        Inyectamos la lista de estaciones del config.json.
        Allowed stations: [{'nombre': 'Retiro', 'id': '3195'}, ...]
        """
        # Creamos un diccionario rápido { 'id': 'nombre' } para buscar fácilmente
        self.station_mapping = {s['id']: s['nombre'] for s in allowed_stations}

    def parse_and_clean(self, raw_data):
        """
        Recibe la lista gigante de la API (datos_raw) y devuelve 
        solo los registros de Madrid con los nombres de las llaves correctos.
        """
        processed_data = []

        for register in raw_data:
            station_id = register.get("indicativo")
            
            # 1. Filtro: ¿Esta estación está en mi lista de Madrid?
            if station_id in self.station_mapping:
                try:
                    # Helper function to convert "13,4" (str) to 13.4 (float)
                    def clean_float(value):
                        if value is None: return None
                        try:
                            return float(str(value).replace(',', '.'))
                        except ValueError:
                            return None
                    # 2. Traducción: Mapeamos los códigos de AEMET a nuestras llaves
                    clean_item = {
                        "name": self.station_mapping[station_id],
                        "indicativo": station_id,
                        "province": register.get("provincia"),
                        "altitude": clean_float(register.get("altitud")),
                        "date": register.get("fecha"), # Fecha/hora de la observación
                        "temp_avg": clean_float(register.get("tmed")),
                        "temp_min": clean_float(register.get("tmin")),
                        "time_temp_min": register.get("horatmin"),
                        "temp_max": clean_float(register.get("tmax")),
                        "time_temp_max": register.get("horatmax"),
                        "wind": clean_float(register.get("racha")),
                        "humidity_avg": clean_float(register.get("hrMedia")), 
                        "humidity_min": clean_float(register.get("hrMin")),
                        "humidity_max": clean_float(register.get("hrMax")),
                        "time_humidity_min": register.get("horahrmin"),
                        "time_humidity_max": register.get("horahrmax"), 
                        "precipitation": clean_float(register.get("prec")),
                        "wind_gust": clean_float(register.get("racha")),
                        "time_wind_gust": register.get("horaracha"),
                        "wind_direction": register.get("dir"),
                        "wind_speed_avg": clean_float(register.get("velmedia")),
                    }
                    
                    # 3. Validación: Solo añadimos si tiene los datos numéricos necesarios
                    if clean_item["temperature"] is not None and clean_item["wind"] is not None:
                        processed_data.append(clean_item)
                    else:
                        logger.warning(f"Datos incompletos en estación {clean_item['name']} (ID: {station_id}) - Registro omitido.")
                        
                except Exception as e:
                    logger.error(f"Error inesperado procesando la estación {station_id}: {e}")

        logger.info(f"Procesados {len(processed_data)} registros válidos de Madrid.")
        return processed_data