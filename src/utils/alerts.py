from utils.logger import configurar_logger

# Inicializamos el logger para el equipo de desarrollo
logger = configurar_logger()

class AlertController:
    def __init__(self, umbrales):
        """
        Inyectamos la sección 'umbrales_alerta' del config.json.
        """
        self.umbrales = umbrales

    def comprobar_alertas(self, registro):
        """
        Función principal que coordina todas las revisiones.
        """
        alertas = []
        alertas.extend(self.comprobar_alerta_temperatura(registro))
        alertas.extend(self.comprobar_alerta_viento(registro))

        if not alertas:
            # Informamos de nivel verde si no hay ninguna alerta en la lista
            return [f"[Nivel Verde]: Sin riesgo detectado en {registro['nombre']}."]

        return alertas

    def comprobar_alerta_temperatura(self, registro):
        alertas = []
        try:
            temp = float(registro["temperatura"])
            u = self.umbrales["temperatura"]
            nombre = registro["nombre"]

            # Comprobaciones dinámicas usando los campos de tu config.json
            if temp >= u["rojo_max"]["valor"]:
                alertas.append(f"{u['rojo_max']['msj']} en {nombre} ({temp}°C)")
            elif temp <= u["rojo_min"]["valor"]:
                alertas.append(f"{u['rojo_min']['msj']} en {nombre} ({temp}°C)")
            elif temp >= u["naranja_max"]["valor"]:
                alertas.append(f"{u['naranja_max']['msj']} en {nombre} ({temp}°C)")
            elif temp <= u["naranja_min"]["valor"]:
                alertas.append(f"{u['naranja_min']['msj']} en {nombre} ({temp}°C)")
            elif temp >= u["amarillo_max"]["valor"]:
                alertas.append(f"{u['amarillo_max']['msj']} en {nombre} ({temp}°C)")
            elif temp <= u["amarillo_min"]["valor"]:
                alertas.append(f"{u['amarillo_min']['msj']} en {nombre} ({temp}°C)")
            
            if alertas:
                logger.warning(f"Alertas de temperatura generadas: {alertas}")

        except (KeyError, ValueError) as e:
            # Si falta un dato o no es un número, el logger nos avisa sin romper el programa
            logger.error(f"Error procesando temperatura en {registro.get('nombre', 'Estación desconocida')}: {e}")

        return alertas

    def comprobar_alerta_viento(self, registro):
        alertas = []
        try:
            viento = float(registro["viento"])
            u = self.umbrales["viento"]
            nombre = registro["nombre"]

            if viento >= u["rojo"]["valor"]:
                alertas.append(f"{u['rojo']['msj']} en {nombre} ({viento} km/h)")
            elif viento >= u["naranja"]["valor"]:
                alertas.append(f"{u['naranja']['msj']} en {nombre} ({viento} km/h)")
            elif viento >= u["amarillo"]["valor"]:
                alertas.append(f"{u['amarillo']['msj']} en {nombre} ({viento} km/h)")
            
            if alertas:
                logger.warning(f"Alertas de viento generadas: {alertas}")

        except (KeyError, ValueError) as e:
            logger.error(f"Error procesando viento en {registro.get('nombre', 'Estación desconocida')}: {e}")

        return alertas