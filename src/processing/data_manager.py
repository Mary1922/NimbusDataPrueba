import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Any

from src.storage import json_handler
from src.processing.models import WeatherRecord, Station
from src.ingestion.api_client import AemetClient
from src.processing.parser import DataParser

class DataManager:
    """
    Data orchestration and persistence layer for Nimbus.
    Manages intelligent caching, AEMET synchronization, and JSON data hierarchy.
    """

    def __init__(self, config_manager: Any) -> None:
        """
        Initializes DataManager with configuration and dependent services.
        
        Args:
            config_manager: Instance of ConfigManager to retrieve paths and filters.
        """
        self.logger = logging.getLogger(__name__)
        self.config = config_manager
        
        # Service Initialization
        self.client = AemetClient()
        self.parser = DataParser()
        
        # Load storage paths from configuration
        storage_cfg = self.config.get_config().get("storage", {})
        self.active_path = storage_cfg.get("active_stations_path", "data/stations/active_stations.json")
        self.catalog_path = storage_cfg.get("stations_catalog_path", "data/stations/stations_catalog.json")
        self.history_path = storage_cfg.get("weather_history_path", "data/weather/history.json")

    @staticmethod
    def _to_iso8601_format(date_str: str) -> str:
        """
        Normalizes a date string to ISO8601 UTC format.
        Example: '2026-05-02' -> '2026-05-02T00:00:00UTC'
        """
        clean_date = date_str.split('+')[0]

        if 'T' not in clean_date:
            return f"{clean_date}T00:00:00UTC"
        
        if not clean_date.endswith("UTC"):
            return f"{clean_date}UTC"
            
        return clean_date

    def _is_today_record_stale(self, last_update_str: str) -> bool:
        """
        Determines if the current day's record should be refreshed based on Time-To-Live (TTL).
        Data is considered stale if the current hour differs from the last update hour.
        """
        now = datetime.now()
        try:
            last_upd = datetime.fromisoformat(last_update_str)
            return now.hour != last_upd.hour or now.day != last_upd.day
        except (ValueError, TypeError):
            return True


    # API REQUEST METHODS

    def _fetch_today_from_api(self, station_id: str) -> List[WeatherRecord]:
        """Fetches real-time hourly observation data from AEMET API."""
        raw_data = self.client.get_today_weather(station_id)
        return self.parser.parse_hourly_weather(raw_data) if raw_data else []

    def _fetch_history_from_api(self, station_id: str, start: str, end: str) -> List[WeatherRecord]:
        """Fetches historical daily climatological data from AEMET API."""
        api_start = self._to_iso8601_format(start)
        api_end = self._to_iso8601_format(end)
        raw_data = self.client.get_daily_weather(station_id, api_start, api_end)
        return self.parser.parse_daily_weather(raw_data) if raw_data else []


    # JSON CACHE METHODS

    def _get_today_from_json(self, station_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves today's record from local JSON cache with O(1) complexity."""
        today_key = date.today().isoformat()
        history = json_handler.load_from_path(self.history_path) or {}
        return history.get(station_id, {}).get("data", {}).get(today_key)

    def _get_history_from_json(self, start: str, end: str, station_id: str) -> List[Dict[str, Any]]:
        """Retrieves historical records within a range from the local JSON cache."""
        history = json_handler.load_from_path(self.history_path) or {}
        results = []
        today_str = date.today().isoformat()
        
        station_node = history.get(station_id, {}).get("data", {})
        for d_str, val in station_node.items():
            # Filter by range and ensure today is excluded (handled separately)
            if start <= d_str <= end and d_str < today_str:
                results.append(val)
        
        return sorted(results, key=lambda x: x['date'])

    def get_records_from_json(self, start: str, end: str, station_id: str) -> List[Dict[str, Any]]:
        """
        Public method to query local JSON for both historical and current day records.
        """
        results = []
        today_str = date.today().isoformat()

        # Fetch historical data (pre-today)
        history_records = self._get_history_from_json(start, end, station_id)
        results.extend(history_records)

        # Add today's record if within requested range
        if start <= today_str <= end:
            today_record = self._get_today_from_json(station_id)
            if today_record:
                results.append(today_record)

        results.sort(key=lambda x: x.get('date', ''))
        return results


    # WEATHER ORCHESTRATION

    def get_weather(self, start_date: str, end_date: str, station_id: str) -> List[Dict[str, Any]]:
        """
        Main entry point for data retrieval. Synchronizes cache and API requests.
        Ensures data integrity for requested historical ranges and dynamic TTL for today.
        """
        today_str = date.today().isoformat()
        final_results = []

        # PHASE 1: Historical Data (Yesterday and older)
        hist_start = start_date
        # Cap end date to yesterday for historical processing
        hist_end = end_date if end_date < today_str else (date.today() - timedelta(days=1)).isoformat()

        if hist_start < today_str:
            local_hist = self._get_history_from_json(hist_start, hist_end, station_id)
            
            # Cache Integrity Check: Verify if any days are missing in the range
            dias_solicitados = (date.fromisoformat(hist_end) - date.fromisoformat(hist_start)).days + 1
            if len(local_hist) < dias_solicitados:
                self.logger.info(f"Faltan datos históricos para {station_id}. Llamando a API...")
                new_api_data = self._fetch_history_from_api(hist_start, hist_end, station_id)
                self.update_weather_history(new_api_data)
                local_hist = self._get_history_from_json(hist_start, hist_end, station_id)
            
            final_results.extend(local_hist)

        # PHASE 2: Real-Time Data (Today's window)
        if end_date >= today_str:
            today_record = self._get_today_from_json(station_id)
            
            refresh_needed = False
            if not today_record:
                refresh_needed = True
            elif self._is_today_record_stale(today_record["last_update"]):
                refresh_needed = True

            if refresh_needed:
                self.logger.info(f"Refrescando ventana horaria de hoy para {station_id}...")
                today_api_data = self._fetch_today_from_api(station_id)
                if today_api_data:
                    self.update_weather_history(today_api_data)
                    today_record = self._get_today_from_json(station_id)

            if today_record:
                final_results.append(today_record)

        return final_results

    def force_api_ingest(self, start_date: str, end_date: str, station_id: str) -> List[WeatherRecord]:
        """
        Bypasses local cache to force a full data refresh from AEMET API.
        Automatically updates local persistence.
        """
        hoy_str = date.today().isoformat()
        all_new_records = []

        # Historical API request
        if start_date < hoy_str:
            # Define the upper bound for the historical data range (excluding current date)
            hist_end = end_date if end_date < hoy_str else (date.today() - timedelta(days=1)).isoformat()
            hist_records = self._fetch_history_from_api(station_id, start_date, hist_end)
            all_new_records.extend(hist_records)

        # Today's API request
        if end_date >= hoy_str:
            today_records = self._fetch_today_from_api(station_id)
            all_new_records.extend(today_records)

        # Persistence update
        if all_new_records:
            self.update_weather_history(all_new_records)
            self.logger.info(f"Ingesta forzada completada: {len(all_new_records)} registros actualizados.")

        return all_new_records


    # PERSISTENCE

    def update_weather_history(self, new_records: List[WeatherRecord]) -> bool:
        """
        Saves records into JSON storage using the Station > Date hierarchy.
        Updates existing entries or creates new station nodes as needed.
        """
        if not new_records: return False

        try:
            history = json_handler.load_from_path(self.history_path) or {}
            
            for record in new_records:
                sid = record.station_id
                if sid not in history:
                    history[sid] = {"metadata": {"name": record.name}, "data": {}}
                
                # Use short date (YYYY-MM-DD) as the unique primary key per station
                short_date = record.date.split('T')[0]
                history[sid]["data"][short_date] = record.to_dict()

            return json_handler.save_to_path(history, self.history_path)
        except Exception as e:
            self.logger.error(f"Error crítico al actualizar histórico JSON: {e}")
            return False


    # STATION MANAGEMENT

    def sync_stations(self) -> bool:
        """Synchronizes station catalog with AEMET and applies configuration filters."""
        self.logger.info("Sincronizando estaciones con AEMET...")
        try:
            raw_data = self.client.get_stations()
            if not raw_data: return False

            # Retrieve filtering criteria from config
            filter_city = self.config.get_config().get("source_config", {}).get("filter_nombre", "MADRID")
            api_stations = self.parser.parse_stations(raw_data, filter_city=filter_city)
            
            # Persist active filtered stations
            update_time = datetime.now().isoformat()
            catalog_data = {
                "metadata": {"last_update": update_time, "count": len(api_stations)},
                "stations": {sid: s.to_dict() for sid, s in api_stations.items()}
            }
            
            return json_handler.save_to_path(catalog_data, self.active_path)
        
        except Exception as e:
            self.logger.error(f"Error en sincronización de estaciones: {e}")
            return False

    def get_active_stations_info(self) -> Dict[str, Any]:
        """
        Returns the complete dictionary of active stations with their metadata.
        Used for rendering detailed tables in the UI.
        """
        data = json_handler.load_from_path(self.active_path) or {}
        return data.get("stations", {})

    def get_active_station_ids(self) -> List[str]:
        """
        Maintains compatibility by returning only the ID list.
        """
        return list(self.get_active_stations_info().keys())