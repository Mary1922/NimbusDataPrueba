import logging
import requests
import os
import time
from dotenv import load_dotenv
from src.logger import log_info, log_error, log_warning
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()

class AemetClient:

    def __init__(self):
        self.api_key = os.getenv("AEMET_API_KEY")
        self.base_url = "https://opendata.aemet.es/opendata/api"
        self.session = requests.Session()

        # Headers obligatorios
        self.session.headers.update({
            "User-Agent": "NimbusData/1.0",
            "api_key": self.api_key
        })
        
        # Configurar reintentos
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)

    def get_weather(self, station_id, start_date, end_date):

        endpoint = f"/valores/climatologicos/diarios/datos/fechaini/{start_date}/fechafin/{end_date}/estacion/{station_id}"
        url = f"{self.base_url}/{endpoint}"

        try:
                # 🔹 PRIMER REQUEST
                start = time.time()
                response = self.session.get(url, timeout=5)
                latency = time.time() - start

                log_info.info(f"STEP1 {url} - {response.status_code} - {latency:.2f}s")

                if response.status_code != 200:
                    log_error.error(f"Error inicial: {response.status_code}")
                    return None

                data_url = response.json().get("datos")

                if not data_url:
                    log_error.error("No se encontró URL de datos")
                    return None

                # 🔹 SEGUNDO REQUEST
                response_data = self.session.get(data_url, timeout=5)

                log_info.info(f"STEP2 {data_url} - {response_data.status_code}")

                if response_data.status_code == 200:
                    return response_data.json()

                elif response_data.status_code == 401:
                    log_error.error("401 usuario no identificado")

                elif response_data.status_code == 403:
                    log_error.error("403 usuario sin permiso de acceso")

                elif response_data.status_code == 404:
                    log_error.error("404 en datos")

                elif response_data.status_code == 429:
                    log_error.error("429 rate limit")

                return None

        except Exception as e:
            log_error.error(f"Error general: {e}")
            return None
        
    def get_stations(self): 

        endpoint = "/valores/climatologicos/inventarioestaciones/todasestaciones"
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.get(url, timeout=5)

            log_info.info(f"GET {url} - {response.status_code}")

            if response.status_code != 200:
                log_error.error(f"Error al obtener estaciones: {response.status_code}")
                return None

            data_url = response.json().get("datos")

            if not data_url:
                log_error.error("No se encontró URL de datos de estaciones")
                return None

            response_data = self.session.get(data_url, timeout=5)

            log_info.info(f"GET {data_url} - {response_data.status_code}")

            if response_data.status_code == 200:
                return response_data.json()

            elif response_data.status_code == 401:
                log_error.error("401 usuario no identificado")

            elif response_data.status_code == 403:
                log_error.error("403 usuario sin permiso de acceso")

            elif response_data.status_code == 404:
                log_error.error("404 en datos de estaciones")

            elif response_data.status_code == 429:
                log_error.error("429 rate limit en datos de estaciones")

            return None

        except Exception as e:
            log_error.error(f"Error general al obtener estaciones: {e}")
            return None