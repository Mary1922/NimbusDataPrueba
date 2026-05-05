# NIMBUS DATA

## 1. Descripción

**NIMBUS DATA** es una aplicación desarrollada para escalar la digitalización de datos climáticos, eliminar la dependencia del factor humano y resolver las limitaciones de latencia, cobertura y escalabilidad. Mediante el consumo de la API **AEMET OpenData**, Nimbus integra una red de sensores virtuales que alimentan un repositorio centralizado para el análisis preventivo y la gestión de riesgos urbanos.

## 2. Objetivos del proyecto

El sistema se ha construido para transformar la gestión de datos municipales basándose en cuatro pilares:

* **Eliminación del 'Apagón de Datos':** Captura automática 24/7 sin latencia humana.
* **Escalabilidad Sin Coste Operativo:** Capacidad de monitorizar nuevas zonas geográficas mediante servidores y no mediante contratación de personal.
* **Centralización:** Unificar registros históricos con alertas municipales para mejorar la respuesta ante eventos climáticos extremos.
* **Auditoría y Transparencia:** Sistema de comparación de discrepancias para validar la precisión de las fuentes externas.

## 3. Tecnologías utilizadas

* **Lenguaje:** Python 3.x.
* **Red:** `Requests` con `HTTPAdapter` para resiliencia ante fallos del servidor.
* **Automatización:** `APScheduler` para la automatización de ciclos de ingesta.
* **Interfaz:** `Tabulate` y códigos de color ANSI (estandarización de alertas según nivel de riesgo).
* **Modelado:** `Dataclasses` para garantizar la integridad de los tipos de datos.
* **Gestión de Entorno:** `python-dotenv` para la seguridad de API Keys.

## 4. Estructura del proyecto

```text
NIMBUS_DATA/
│
├── data/                       # Base de datos (JSON)
│   ├── stations/               # Metadatos de la red de estaciones
│   └── weather/                # Series temporales de mediciones
├── src/                        # Núcleo del sistema
│   ├── ingestion/              # Clientes de red (api_client.py)
│   ├── processing/             # Lógica de negocio (data_manager.py, parser.py, models.py)
│   ├── storage/                # Capa de persistencia (json_handler.py)
│   ├── utils/                  # Herramientas (config_manager.py, logger.py, scheduler.py)
│   └── main.py                 # Punto de entrada y orquestador de UI
├── tests/                      # Pruebas (test_api_client.py, test_parser.py, test_storage.py)
├── logs/                       # Trazabilidad técnica y operativa
├── .env                        # Variables sensibles
├── config.json                 # Umbrales de alerta y configuración global
└── requirements.txt            # Dependencias del ecosistema Python
```

## 5. Arquitectura y componentes

La estructura de carpetas de tipo **Pipeline** (Ingestion ➔ Processing ➔ Storage) implementada responde a una arquitectura de **separación de responsabilidades**. Las principales razones técnicas son:

* **Desacoplamiento de la Fuente de Datos** (`src/ingestion`)
  Al tener el `api_client.py` aislado, si la fuente cambia, solo habría que tocar esa carpeta. El resto del sistema no se entera ni se rompe, porque siempre reciben los datos ya procesados.

* **Normalización de Datos Heterogéneos** (`src/processing`)
  En `processing/parser.py` es donde ocurre la conversión de datos crudos en objetos de Python puros (`models.py`). Esto asegura que el sistema siempre trabaje con **datos estándar**, independientemente de la fuente.

* **Independencia de la Persistencia** (`src/storage`)
  Gracias al diseño modular del `json_handler.py` si el Ayuntamiento decidiese usar una base de datos SQL, solo habría que ese "conector". La lógica de negocio no se verá afectada.

* **Orquestación y Automatización** (`src/utils`)
  El uso de un `scheduler.py` y un `config_manager.py` responde a la necesidad de **escalabilidad**. Separar las utilidades permite que el **scheduler** ejecute ciclos de limpieza y descarga en segundo plano mientras el usuario sigue usando el menú principal.

### Componentes principales

* **AemetClient:** Implementa un sistema de descarga en dos pasos con factor de retroceso exponencial (*backoff*), garantizando la conectividad incluso bajo políticas estrictas de *Rate Limiting*.
* **DataManager:** Orquestador que realiza una fusión inteligente de datos, detectando solapamientos y gestionando la integridad del historial.
* **DataParser:** Responsable de la **normalización**. Transforma los formatos heterogéneos de la API en tipos de datos estándar de Python para análisis.

## 6. Flujo de datos

1. **Ingesta:** El cliente solicita datos a la API.
2. **Normalización:** El Parser estandariza unidades y formatos.
3. **Evaluación:** El AlertController aplica los umbrales de seguridad urbana.
4. **Almacenamiento:** El JsonHandler persiste los registros en la jerarquía documental.

```text
        [API AEMET] -> [api_client] -> [parser] -> [data_manager] -> [json_handler] <-> [JSON]
                                                                          |
                                                                          v
                                                [AlertController] -> [main.py (UI)]
```

## 7. Caché Inteligente con TTL Dinámico

Nimbus utiliza una estrategia de almacenamiento eficiente basada en la naturaleza del dato:

* **Histórico (TTL Infinito):** Los datos consolidados de fechas pasadas se marcan como inmutables para ahorrar cuota de API.
* **Tiempo Real (TTL 60m):** Los datos del día actual tienen un "tiempo de vida" dinámico; se refrescan automáticamente si el último acceso supera la hora de antigüedad, garantizando que el Departamento siempre trabaje con información actualizada.

## 8. Estructura de datos

* **`active_stations.json`**

```json
{
    "stations": {
        "3195": {
            "station_id": "3195",
            "name": "MADRID, RETIRO",
            "province": "MADRID",
            "latitude": "402442N",
            "longitude": "034041W",
            "altitude": "667"
        }
    }
}
```

* **`history.json`**

```json
{
              "data": {
        "2026-05-01": {
            "date": "2026-05-01T23:00:00UTC",
            "station_id": "3129",
            "name": "MADRID/BARAJAS",
            "temp_avg": 17.4,
            "temp_min": 13.7,
            "temp_max": 25.2,
            "humidity_avg": 70.0,
            "precipitation": 0.0,
            "wind_direction": 150.0,
            "wind_speed_avg": 4.5,
            "last_update": "2026-05-02T00:00:00"
        }
    }
}
```

## 9. Sistema de alertas

El motor de alertas sigue los niveles de aviso oficiales:

* **Escala de Alertas por Temperatura**

El sistema monitoriza tanto los extremos de calor como los de frío para proteger la salud pública y la infraestructura.

| Nivel de Riesgo | Color | Rango Máximas (Calor) | Rango Mínimas (Frío) | Mensaje Operativo |
| :--- | :--- | :--- | :--- | :--- |
| **Crítico** | Rojo | **> 42.0 °C** | **< -10.0 °C** | Riesgo calor extremo / Heladas severas. |
| **Importante** | Naranja | **39.0 a 42.0 °C** | **-10.0 a -6.0 °C** | Riesgo importante. Evitar exteriores. |
| **Precaución** | Amarillo | **36.0 a 39.0 °C** | **-6.0 a -4.0 °C** | Precaución. Posibilidad de hielo/calor. |

* **Escala de Alertas por Viento**
  
Los umbrales de viento están diseñados para la gestión de la seguridad en parques, vía pública y elementos en altura.

| Nivel de Riesgo | Color | Velocidad Viento | Acción / Mensaje Operativo |
| :--- | :--- | :--- | :--- |
| **Crítico** | Rojo | **> 110.0 km/h** | **¡Alerta de viento fuerte!** Riesgo de caída de objetos. |
| **Importante** | Naranja | **90.0 a 110.0 km/h** | **Viento fuerte.** Precaución y cierre de parques. |
| **Precaución** | Amarillo | **70.0 a 90.0 km/h** | **Viento moderado.** Precaución en exteriores. |

## 10 Instalación y configuración

  1. Clonar el repositorio:

```bash
git clone https://github.com/HelenDiMo/NimbusData.git nimbus`
cd nimbus
```

  2. Crear y activar el entorno virtual (`venv`):

```bash
python -m venv .venv
# En Windows:
.\.venv\Scripts\activate
# En Linux/Mac:
source .venv/bin/activate
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Configuracón del archivo de entorno `.env`:

  * Solicitar la clave de acceso en  [AEMET OpenData](https://opendata.aemet.es/centrodedescargas/inicio).
 
  * En la raíz del proyecto, crear un archivo `.env`:

    ```bash
    touch .env
    ```
  * Abrir el archivo y añadir la clave con el siguiente formato:
  
    ```text
    AEMET_API_KEY="tu_api_key_aqui_entre_comillas"
    ```

5. Ejecutar la aplicación:

```bash
python -m src.main
```

## 11. Funcionalidades principales

* **Sincronización en Background:** El `NimbusScheduler` descarga datos cada 60 min en segundo plano.
* **Comparador de Discrepancias:** Herramienta de auditoría para validar la veracidad de los datos externos frente al histórico local.
* **Gestión de Estaciones:** Capacidad de activar o desactivar distritos de monitoreo según la necesidad del ayuntamiento.

##### Menú principal:

 ```text
                                ==================================================
                                                    NIMBUS DATA
                                ==================================================
                                        [1] Ingesta Automática (AEMET)
                                        [2] Ver Historico de Datos
                                        [3] Comparativa de Fuentes
                                        [4] Configurar Scheduler
                                        [5] Gestión de Estaciones
                                        [X] Salir
                                
                                (Ctrl+C para Salir del programa)
                                Selecciona una opción:
 ```

## 12. Pruebas automatizadas

Se incluye una suite de pruebas con `pytest` para asegurar la calidad del software:

* Validación de la lógica de alertas.
* Pruebas de carga y escritura de JSON.
* Mocking de la API para evitar consumo innecesario de créditos durante el desarrollo.

Para ejecutar los tests, utiliza el siguiente comando:

```python
pytest
```

## 13. Logs

El sistema implementa **Logging** para auditoría interna del departamento, diferenciando entre eventos de depuración y errores críticos de red.

## 14. Evaluación Ética y Gobierno del Dato

El desarrollo de **NIMBUS DATA** se alinea con los principios de responsabilidad, transparencia y sostenibilidad en el uso de recursos públicos. Se han identificado y mitigado los siguientes aspectos clave:

* **Uso Responsable de Datos Abiertos (OpenData)**. El sistema implementa límites de frecuencia en las peticiones y una gestión eficiente de la API Key para evitar el abuso de los servicios públicos y garantizar la disponibilidad para otros usuarios.

* **Seguridad y Privacidad**:
  * **Gestión de Credenciales:** Las API Keys se administran exclusivamente mediante variables de entorno (`.env`), eliminando cualquier exposición en el código fuente o repositorios públicos.
  * **Naturaleza de los Datos:** El proyecto procesa únicamente información meteorológica. No se maneja información personal identificable (PII), por lo que el riesgo para la privacidad individual es nulo.

* **Transparencia y Trazabilidad**:
  * **Integridad del Dato:** Se garantiza la trazabilidad completa del flujo de datos. Las transformaciones (normalización y parsing) están documentadas para asegurar que los datos procesados no se presenten como originales, evitando interpretaciones erróneas.
  * **Contextualización:** El sistema reconoce limitaciones intrínsecas como posibles retrasos en la actualización o dependencia de la cobertura de estaciones específicas.

* **Automatización Ética**:
  * **Eficiencia de Recursos:** El uso de un *scheduler* está configurado para minimizar el impacto en el servicio público, permitiendo ajustar los intervalos de ejecución para un consumo equilibrado y justificado de los recursos de red.

* **Gestión del Almacenamiento**:
  * **Principio de Minimización:** Solo se almacenan los datos necesarios para el análisis meteorológico urbano, evitando la acumulación innecesaria de datos y manteniendo una gestión organizada en formato JSON.

## 15. Mejoras futuras

* **Automatización Cloud**:
  * **GitHub Actions:** Migración del Scheduler a la nube para ejecución automática cada hora.
  * **Auto-Update:** Commits automáticos de datos al repositorio para convertirlo en un sistema auto-actualizable.

* **Interfaz Visual Conectada**:
  * **Streamlit / Dash:** Implementación de un Dashboard visual con mapas interactivos de estaciones y gráficos de tendencias históricas.
  
* **Arquitectura Profesional Desacoplada**:
  * **FastAPI:** Exposición de los datos locales a través de una API propia.
  * **Base de Datos:** Migración de archivos JSON a una base de datos real (PostgreSQL/MongoDB).
  * **Frontend Moderno:** Interfaz web independiente construida en React conectada a la nueva API.

---