from datetime import date, timedelta

from src.utils.config_manager import ConfigManager
from src.processing.data_manager import DataManager


def run():

    # Inicializar configuración
    config = ConfigManager()

    # Inicializar DataManager
    manager = DataManager(config)

    print("Sincronizando estaciones...")

    # Actualizar estaciones
    manager.sync_stations()

    # Obtener IDs activas
    station_ids = manager.get_active_station_ids()

    print(f"Estaciones encontradas: {len(station_ids)}")

    # Fechas
    end_date = date.today().isoformat()
    start_date = (date.today() - timedelta(days=1)).isoformat()

    # Ingesta estación por estación
    for station_id in station_ids:

        print(f"Ingeriendo datos de estación {station_id}")

        try:
            manager.force_api_ingest(
                start_date=start_date,
                end_date=end_date,
                station_id=station_id
            )

        except Exception as e:
            print(f"Error en estación {station_id}: {e}")

    print("Ingesta automática completada")


if __name__ == "__main__":
    run()