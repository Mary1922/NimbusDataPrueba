import requests
import os
import time
from dotenv import load_dotenv
from src.logger import log_info, log_error

load_dotenv()

API_KEY = os.getenv("API_KEY")


def obtener_datos_madrid():
    url = "https://opendata.aemet.es/opendata/api/observacion/convencional/todas"

    headers = {
        "api_key": API_KEY,
        "User-Agent": "NimbusData/1.0"
    }

    for intento in range(3):
        try:
            inicio = time.time()

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                log_error(f"HTTP {response.status_code}")
                time.sleep(2)
                continue

            data = response.json()
            datos_url = data.get("datos")

            response_datos = requests.get(datos_url, timeout=10)

            if response_datos.status_code != 200:
                log_error("Error en datos finales")
                return None

            datos = response_datos.json()

            # 🔴 FILTRAR MADRID
            madrid = [
                d for d in datos
                if "MADRID" in d.get("ubi", "").upper()
            ]

            duracion = time.time() - inicio
            log_info(f"Madrid OK - {duracion:.2f}s")

            return madrid

        except Exception as e:
            log_error(f"Error: {e}")
            time.sleep(2)

    return None