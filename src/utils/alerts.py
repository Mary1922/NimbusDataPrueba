from logger import config_logger

# Inicializamos el logger para el equipo de desarrollo
logger = config_logger()

class AlertController:
    def __init__(self, thresholds):
        """
        Inyectamos la sección 'umbrales_alerta' del config.json.
        """
        self.thresholds = thresholds

    def check_alerts(self,register):
        """
        Función principal que coordina todas las revisiones.
        """
        alerts = []
        alerts.extend(self.check_temperature_alerts(register))
        alerts.extend(self.check_wind_alerts(register))

        if not alerts:
            # Informamos de nivel verde si no hay ninguna alerta en la lista
            return [f"[Nivel Verde]: Sin riesgo detectado en {register['nombre']}."]

        return alerts

    def check_temperature_alerts(self, register):
        alerts = []
        try:
            temp = float(register["temperatura"])
            u = self.umbrales["temperatura"]
            nombre = register["nombre"]

            # Comprobaciones dinámicas usando los campos de tu config.json
            if temp >= u["red_max"]["value"]:
                alerts.append(f"{u['red_max']['msg']} en {nombre} ({temp}°C)")
            elif temp <= u["red_min"]["value"]:
                alerts.append(f"{u['red_min']['msg']} en {nombre} ({temp}°C)")
            elif temp >= u["orange_max"]["value"]:
                alerts.append(f"{u['orange_max']['msg']} en {nombre} ({temp}°C)")
            elif temp <= u["orange_min"]["value"]:
                alerts.append(f"{u['orange_min']['msg']} en {nombre} ({temp}°C)")
            elif temp >= u["yellow_max"]["value"]:
                alerts.append(f"{u['yellow_max']['msg']} en {nombre} ({temp}°C)")
            elif temp <= u["yellow_min"]["value"]:
                alerts.append(f"{u['yellow_min']['msg']} en {nombre} ({temp}°C)")

            if alerts:
                logger.warning(f"Alertas de temperatura generadas: {alerts}")

        except (KeyError, ValueError) as e:
            # Si falta un dato o no es un número, el logger nos avisa sin romper el programa
            logger.error(f"Error procesando temperatura en {register.get('nombre', 'Estación desconocida')}: {e}")

        return alerts

    def check_wind_alerts(self, register):
        alerts = []
        try:
            wind = float(register["viento"])
            u = self.umbrales["viento"]
            nombre = register["nombre"]

            if wind >= u["red"]["value"]:
                alerts.append(f"{u['red']['msg']} en {nombre} ({wind} km/h)")
            elif wind >= u["orange"]["value"]:
                alerts.append(f"{u['orange']['msg']} en {nombre} ({wind} km/h)")
            elif wind >= u["yellow"]["value"]:
                alerts.append(f"{u['yellow']['msg']} en {nombre} ({wind} km/h)")

            if alerts:
                logger.warning(f"Alertas de viento generadas: {alerts}")

        except (KeyError, ValueError) as e:
            logger.error(f"Error procesando viento en {register.get('nombre', 'Estación desconocida')}: {e}")

        return alerts