from utils.logger import configurar_logger

# Inicializamos el logger para registrar el proceso de limpieza
logger = configurar_logger()

class DataParser:
    def __init__(self, estaciones_permitidas):
        """
        Inyectamos la lista de estaciones del config.json.
        estaciones_permitidas: [{'nombre': 'Retiro', 'id': '3195'}, ...]
        """
        # Creamos un diccionario rápido { 'id': 'nombre' } para buscar fácilmente
        self.mapeo_estaciones = {e['id']: e['nombre'] for e in estaciones_permitidas}

    def filtrar_y_limpiar(self, datos_raw):
        """
        Recibe la lista gigante de la API (datos_raw) y devuelve 
        solo los registros de Madrid con los nombres de las llaves correctos.
        """
        datos_procesados = []

        for registro in datos_raw:
            id_estacion = registro.get("idema")
            
            # 1. Filtro: ¿Esta estación está en mi lista de Madrid?
            if id_estacion in self.mapeo_estaciones:
                try:
                    # 2. Traducción: Mapeamos los códigos de AEMET a nuestras llaves
                    # 'ta' -> temperatura
                    # 'vv' -> viento
                    item_limpio = {
                        "nombre": self.mapeo_estaciones[id_estacion],
                        "temperatura": registro.get("ta"),
                        "viento": registro.get("vv"),
                        "fecha": registro.get("fint") # Fecha/hora de la observación
                    }
                    
                    # 3. Validación: Solo añadimos si tiene los datos numéricos necesarios
                    if item_limpio["temperatura"] is not None and item_limpio["viento"] is not None:
                        datos_procesados.append(item_limpio)
                    else:
                        logger.warning(f"Datos incompletos en estación {item_limpio['nombre']} (ID: {id_estacion})")
                        
                except Exception as e:
                    logger.error(f"Error inesperado procesando la estación {id_estacion}: {e}")

        logger.info(f"Procesados {len(datos_procesados)} registros válidos de Madrid.")
        return datos_procesados