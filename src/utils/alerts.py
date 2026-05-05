import logging
from src.utils.config_manager import ConfigManager

class AlertController:
    def __init__(self):
        """
        Carga los umbrales desde el ConfigManager.
        """
        config = ConfigManager().get_config()
        self.thresholds = config.get("alert_thresholds", {})
        self.logger = logging.getLogger(__name__)

    def check_alerts(self, register):
        """
        Coordina las revisiones de temperatura y viento.
        """
        if not self.thresholds:
            self.logger.error("No se pudieron cargar los umbrales de alerta (alert_thresholds vacío).")
            return [f"[Error]: Configuración de alertas no disponible."]

        alerts = []
        alerts.extend(self.check_temperature_alerts(register))
        alerts.extend(self.check_wind_alerts(register))

        if not alerts:
            # Informamos de nivel verde si no hay ninguna alerta
            return [f"[Nivel Verde]: Sin riesgo detectado en {register.get('nombre', 'la estación')}."]

        return alerts

    def check_temperature_alerts(self, register):
        alerts = []
        try:
            # Validación de datos de entrada
            if "temp_avg" not in register or register["temp_avg"] is None:
                return alerts

            temp = float(register["temp_avg"])
            u = self.thresholds.get("temp_avg")
            nombre = register.get("nombre", "Desconocida")

            if not u: return alerts

            # Comprobaciones de niveles (de mayor a menor gravedad)
            if temp >= u["red_max"]["value"]:
                alerts.append(f"{u['red_max']['msg']} en {nombre} ({temp} °C)")
            elif temp <= u["red_min"]["value"]:
                alerts.append(f"{u['red_min']['msg']} en {nombre} ({temp} °C)")
            
            elif temp >= u["orange_max"]["value"]:
                alerts.append(f"{u['orange_max']['msg']} en {nombre} ({temp} °C)")
            elif temp <= u["orange_min"]["value"]:
                alerts.append(f"{u['orange_min']['msg']} en {nombre} ({temp} °C)")
            
            elif temp >= u["yellow_max"]["value"]:
                alerts.append(f"{u['yellow_max']['msg']} en {nombre} ({temp} °C)")
            elif temp <= u["yellow_min"]["value"]:
                alerts.append(f"{u['yellow_min']['msg']} en {nombre} ({temp} °C)")

            if alerts:
                self.logger.warning(f"Alertas de temperatura en {nombre}: {alerts}")

        except (KeyError, ValueError, TypeError) as e:
            self.logger.error(f"Error procesando temperatura en {register.get('nombre')}: {e}")

        return alerts

    def check_wind_alerts(self, register):
        alerts = []
        try:
            if "wind_speed_avg" not in register or register["wind_speed_avg"] is None:
                return alerts

            wind = float(register["wind_speed_avg"])
            u = self.thresholds.get("wind_speed_avg") # Corregido: antes decía self.umbrales
            nombre = register.get("nombre", "Desconocida")

            if not u: return alerts

            if wind >= u["red"]["value"]:
                alerts.append(f"{u['red']['msg']} en {nombre} ({wind} km/h)")
            elif wind >= u["orange"]["value"]:
                alerts.append(f"{u['orange']['msg']} en {nombre} ({wind} km/h)")
            elif wind >= u["yellow"]["value"]:
                alerts.append(f"{u['yellow']['msg']} en {nombre} ({wind} km/h)")

            if alerts:
                self.logger.warning(f"Alertas de viento en {nombre}: {alerts}")

        except (KeyError, ValueError, TypeError) as e:
            self.logger.error(f"Error procesando viento en {register.get('nombre')}: {e}")

        return alerts

    def get_color_for_temp(self, temp):
        if temp is None or temp == "" or temp == "--": return None
        try:
            val = float(temp)
            # Intentamos obtener los umbrales buscando varias claves posibles
            u = self.thresholds.get("temperature") or self.thresholds.get("temp_avg")
            if not u: return None

            if val >= u["red_max"]["value"] or val <= u["red_min"]["value"]: return "#F85149"
            if val >= u["orange_max"]["value"] or val <= u["orange_min"]["value"]: return "#F0883E"
            if val >= u["yellow_max"]["value"] or val <= u["yellow_min"]["value"]: return "#F1C40F"
        except: pass
        return None

    def get_color_for_wind(self, wind):
        if wind is None or wind == "" or wind == "--": return None
        try:
            val = float(wind)
            u = self.thresholds.get("wind") or self.thresholds.get("wind_speed_avg")
            if not u: return None

            if val >= u["red"]["value"]: return "#F85149"
            if val >= u["orange"]["value"]: return "#F0883E"
            if val >= u["yellow"]["value"]: return "#F1C40F"
        except: pass
        return None