import os
import sys
import logging
import platform
import subprocess
from datetime import datetime
from tabulate import tabulate

from src.utils.logger import config_logger
from src.utils.config_manager import ConfigManager
from src.processing.data_manager import DataManager
from src.storage import json_handler
from src.utils.alerts import AlertController
from src.utils.scheduler import NimbusScheduler

# CONFIGURATION
RESET = "\033[0m"

# ANSI Mapping for Alert Colors
HEX_TO_ANSI = {
    "#F85149": "\033[91m", # Red (Alert/KO)
    "#F0883E": "\033[93m", # Orange
    "#F1C40F": "\033[33m", # Yellow
    "GREEN":   "\033[92m", # Green (OK)
    "BLUE":    "\033[94m"  # Blue (New Record)
}

# DATE VALIDATION

def request_start_date(today_str: str, today_dt: datetime) -> datetime:
    """Requests and validates the start date (cannot be in the future)."""
    while True:
        entry = input(f"Fecha Inicio (YYYY-MM-DD) [[Enter] hoy: {today_str}]: ").strip() or today_str
        try:
            date_dt = datetime.strptime(entry, "%Y-%m-%d")
            if date_dt > today_dt:
                print(f"[!] Error: La fecha de inicio no puede ser futura.")
                continue
            return date_dt
        except ValueError:
            print("[!] Error: Formato incorrecto. Use YYYY-MM-DD (ej: 2024-03-15).")

def request_end_date(start_dt: datetime, today_dt: datetime, today_str: str) -> datetime:
    """Requests and validates the end date (must be >= start and <= today)."""
    while True:
        entry = input(f"Fecha Fin    (YYYY-MM-DD) [[Enter] hoy: {today_str}]: ").strip() or today_str
        try:
            date_dt = datetime.strptime(entry, "%Y-%m-%d")
            if date_dt > today_dt:
                print(f"[!] Error: La fecha fin no puede ser futura.")
                continue
            if date_dt < start_dt:
                print(f"[!] Error: La fecha fin debe ser igual o posterior a la fecha de inicio ({start_dt.strftime('%Y-%m-%d')}).")
                continue
            return date_dt
        except ValueError:
            print("[!] Error: Formato incorrecto. Use YYYY-MM-DD.")

# INTERFACE UTILS

def clear_screen():
    """
    Clears the terminal console based on the operating system.
    """
    try:
        print("\033[H\033[2J", end="", flush=True)
        is_windows = platform.system() == "Windows"
        cmd = "cls" if is_windows else "clear"
        subprocess.run(cmd, shell=is_windows, check=True)
    except Exception:
        print("\033[H\033[2J", end="")

def main_menu():
    """
    Displays the primary Nimbus Data navigation menu.
    
    Returns:
        str: The user's menu selection.
    """
    print("\n" + "="*50)
    print("                   NIMBUS DATA")
    print("="*50)
    print("        [1] Ingesta Automática (AEMET)")
    print("        [2] Ver Historico de Datos")
    print("        [3] Comparativa de fuentes")
    print("        [4] Configurar Scheduler")
    print("        [5] Gestión de Estaciones")
    print("        [X] Salir")
    print("\n(Ctrl+C para Salir del programa)")
    return input("Selecciona una opción: ").strip()

def select_stations(data_manager, active=True):
    """
    Lists available stations and allows the user to select one or all.
    
    Args:
        data_manager (DataManager): The instance managing station files.
        active (bool): If True, loads only active stations; else loads the full catalog.
        
    Returns:
        list: A list of tuples (station_id, station_name). Returns None if no stations found.
    """
    path = data_manager.active_path if active else data_manager.catalog_path
    if not os.path.exists(path):
        data_manager.sync_stations()

    data = json_handler.load_from_path(path) or {}
    stations_dict = data.get("stations", {})
    if not stations_dict: return None

    ids_list = list(stations_dict.keys())
    processed_stations = []
    print("\nEstaciones disponibles:")
    print("-" * 55)

    for i, s_id in enumerate(ids_list, 1):
        info = stations_dict[s_id]
        full_name = info.get('name', 'Sin nombre')
        station_name = full_name.split(", ", 1)[1] if ", " in full_name else full_name
        processed_stations.append((s_id, station_name))
        print(f"[{i}] {station_name:<30} (ID: {s_id})")

    while True:
        try:
            selection = input("\nSelecciona una estación ([Enter] todas): ").strip()
            if selection == "": return processed_stations 
            idx = int(selection) - 1
            if 0 <= idx < len(processed_stations): return [processed_stations[idx]]
        except (ValueError, IndexError):
            print("[!] Selección no válida.")

# OPTION LOGIC

def option_automatic_ingestion(data_manager, alerts):
    """
    Handles the manual triggering of API downloads for specific dates and stations.
    """
    while True:
        try:
            clear_screen()
            print("\n" + "="*70)
            print("--- [1] INGESTA AUTOMÁTICA (Sincronización API AEMET) ---")
            print("="*70)

            target_stations = select_stations(data_manager)
            if not target_stations: break

            today_dt = datetime.now()
            today_str = today_dt.strftime("%Y-%m-%d")
            
            dt_ini = request_start_date(today_str, today_dt)
            dt_fin = request_end_date(dt_ini, today_dt, today_str)
            start, end = dt_ini.strftime("%Y-%m-%d"), dt_fin.strftime("%Y-%m-%d")

            for s_id, s_name in target_stations:
                print(f"\n[API] Descargando: {s_name} ({s_id})...")
                # Invoke method to fetch and persist data
                new_records = data_manager.force_api_ingest(start, end, s_id)

                if new_records:
                    table_data = []
                    headers = ["FECHA", "TEMPERATURA (°C)", "HUMEDAD (%)", "VIENTO (km/h)"]
                    
                    for r in new_records:
                        # Retrieve ANSI color codes from AlertController
                        c_t = HEX_TO_ANSI.get(alerts.get_color_for_temp(r.temp_avg), "")
                        c_v = HEX_TO_ANSI.get(alerts.get_color_for_wind(r.wind_speed_avg), "")
                        
                        # Format values
                        f_clean = r.date.split('T')[0] if r.date else "--"
                        
                        # Apply color + value + RESET
                        t_str = f"{c_t}{r.temp_avg:.1f}{RESET}" if r.temp_avg is not None else "--"
                        h_str = f"{r.humidity_avg}" if r.humidity_avg is not None else "--"
                        v_str = f"{c_v}{r.wind_speed_avg:.1f}{RESET}" if r.wind_speed_avg is not None else "--"
                        
                        table_data.append([f_clean, t_str, h_str, v_str])
                    
                    # Render table using tabulate
                    print(f"\nRESULTADOS: {s_name.upper()}")
                    print(tabulate(table_data, headers=headers, tablefmt="grid", stralign="center"))
                else:
                    print(f"[!] No se recibieron datos para {s_name}.")

            if input("\n¿Desea realizar otra sincronización? (s/n): ").lower() != 's': 
                break

        except KeyboardInterrupt: 
            break

def option_view_history(data_manager, alerts):
    """
    Fetches and displays historical weather data stored locally in JSON files.
    """
    while True:
        try:
            clear_screen()
            print("\n--- [2] CONSULTA DE HISTÓRICO ---")
            target_stations = select_stations(data_manager)
            if not target_stations: return 

            today_dt = datetime.now()
            today_str = today_dt.strftime("%Y-%m-%d")

            # Validation
            dt_ini = request_start_date(today_str, today_dt)
            dt_fin = request_end_date(dt_ini, today_dt, today_str)
            
            start, end = dt_ini.strftime("%Y-%m-%d"), dt_fin.strftime("%Y-%m-%d")

            for s_id, s_name in target_stations:
                records = data_manager.get_weather(start, end, s_id)
                if records:
                    print(f"\nESTACIÓN: {s_name.upper()}\n")
                    
                    tabla_datos = []
                    headers = ["FECHA", "TEMPERATURA (°C)", "HUMEDAD (%)", "VELOCIDAD (km/h)"]

                    for r in records:
                        # 1. Get alert color mappings
                        color_t = HEX_TO_ANSI.get(alerts.get_color_for_temp(r.get('temp_avg')), "")
                        color_w = HEX_TO_ANSI.get(alerts.get_color_for_wind(r.get('wind_speed_avg')), "")

                        # Formatear valores
                        t_raw = r.get('temp_avg')
                        t_str = f"{color_t}{t_raw:.1f}{RESET}" if t_raw is not None else "--"
                        
                        w_raw = r.get('wind_speed_avg')
                        w_str = f"{color_w}{w_raw:.1f}{RESET}" if w_raw is not None else "--"
                        
                        h_str = r.get('humidity_avg', "--")
                        f_str = r.get('date', '--')[:10]

                        tabla_datos.append([f_str, t_str, h_str, w_str])

                    print(tabulate(tabla_datos, headers=headers, tablefmt="grid", stralign="center"))
                else:
                    print(f"\n[!] No hay registros para {s_name}.")
            
            if input("\n¿Quieres hacer otra consulta? (s/n): ").lower() != 's': break
        
        except KeyboardInterrupt:
            break

def option_comparison_discrepancies(data_manager, alerts):
    """
    Compares local JSON data against fresh API data to identify missing entries or value mismatches.
    Uses a dynamic double-header table for better visualization.
    """
    while True:
        try:
            clear_screen()
            print("\n" + "="*80)
            print("--- [3] COMPARATIVA Y DISCREPANCIAS (Local vs API) ---")
            print("="*80)

            result = select_stations(data_manager)
            if not result: break 
            
            s_id, s_name = result[0]
            today_dt = datetime.now()
            today_str = today_dt.strftime("%Y-%m-%d")

            dt_ini = request_start_date(today_str, today_dt)
            dt_fin = request_end_date(dt_ini, today_dt, today_str)
            start, end = dt_ini.strftime("%Y-%m-%d"), dt_fin.strftime("%Y-%m-%d")

            # Data retrieval and cross-referencing
            local_h = data_manager.get_records_from_json(start, end, s_id)
            records_json = {r['date'].split('T')[0]: r for r in local_h}
            
            api_h = data_manager.force_api_ingest(start, end, s_id)
            records_api = {r.date.split('T')[0]: r for r in api_h}

            all_dates = sorted(set(records_json.keys()) | set(records_api.keys()))

            def fmt(val):
                if val is None or val == '--': return "--"
                try: return f"{float(val):.1f}"
                except: return "--"

            table_rows = []
            sub_headers = ["FECHA", "JSON", "API", "JSON", "API", "JSON", "API", "ESTADO"]

            # Row construction and color logic
            for f in all_dates:
                rj = records_json.get(f, {})
                ra = records_api.get(f)
                
                tj, ta = fmt(rj.get('temp_avg')), fmt(getattr(ra, 'temp_avg', None))
                hj, ha = fmt(rj.get('humidity_avg')), fmt(getattr(ra, 'humidity_avg', None))
                vj, va = fmt(rj.get('wind_speed_avg')), fmt(getattr(ra, 'wind_speed_avg', None))

                json_vacio = all(v == "--" for v in [tj, hj, vj])
                api_vacia = all(v == "--" for v in [ta, ha, va])
                
                if json_vacio and api_vacia:
                    status = "--"
                elif json_vacio and not api_vacia:
                    status = f"{HEX_TO_ANSI['BLUE']}NUEVO{RESET}"
                else:
                    diff = False
                    for v1, v2 in [(tj, ta), (hj, ha), (vj, va)]:
                        if v1 != "--" and v2 != "--":
                            if abs(float(v1) - float(v2)) > 0.01:
                                diff = True
                                break
                    
                    status = f"{HEX_TO_ANSI['#F85149']}KO{RESET}" if diff else f"{HEX_TO_ANSI['GREEN']}OK{RESET}"

                table_rows.append([f, tj, ta, hj, ha, vj, va, status])

            # Double Header Rendering
            if table_rows:
                # Generate the base table with tabulate to retrieve the layout structure
                base_table = tabulate(table_rows, headers=sub_headers, tablefmt="grid", stralign="center")
                lines = base_table.split("\n")
                
                parts = lines[1].split('|')
                
                def get_width(indices):
                    # Sum the widths of the specified columns plus internal '|' separators
                    return sum(len(parts[i]) for i in indices) + (len(indices) - 1)

                w_fec  = len(parts[1])
                w_temp = get_width([2, 3])
                w_hum  = get_width([4, 5])
                w_wind = get_width([6, 7])
                w_stat = len(parts[8])

                # Manually build the super-header row
                super_header = (
                    f"|{ ' ' * w_fec }|"
                    f"{'TEMPERATURA (°C)':^{w_temp}}|"
                    f"{'HUMEDAD (%)':^{w_hum}}|"
                    f"{'VIENTO (km/h)':^{w_wind}}|"
                    f"{ ' ' * w_stat }|"
                )

                print(f"\nESTACIÓN: {s_name.upper()} ({s_id})")
                print(lines[0])         
                print(super_header)       
                print(base_table)         
            else:
                print(f"\n[!] No hay datos para comparar en el rango {start} a {end}.")

            if input("\n¿Desea realizar otra comparación? (s/n): ").lower() != 's': 
                break
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n[ERROR] Ocurrió un fallo en la comparativa: {e}")
            break

def option_station_management(data_manager):
    """
    Provides a submenu for managing meteorological stations within the system.

    This function allows the user to:
    1. View technical details (ID, Name, Coordinates, Altitude) of stations 
       currently marked as active in the local configuration.
    2. Synchronize the local station catalog with the official AEMET API to 
       ensure the metadata is up to date.

    Args:
        data_manager (DataManager): The instance responsible for handling station 
                                    metadata and API synchronization logic.
    """
    while True:
        try:
            clear_screen()
            print("\n" + "="*95)
            print("--- [5] GESTIÓN DE ESTACIONES ---")
            print("="*95)
            print("[1] Ver estaciones activas (Detalles Técnicos)")
            print("[2] Sincronizar catálogo con AEMET")
            print("[X] Volver al menú principal")
            print("="*95)
            
            sub = input("\nSelecciona una opción: ").strip().upper()

            if sub == "1":
                print("\n[ESTACIONES ACTIVAS - DETALLES TÉCNICOS]")
                estaciones = data_manager.get_active_stations_info()
                
                if estaciones:
                    # Table configuration
                    header = f"| {'ID':^8} | {'NOMBRE':^25} | {'LATITUD':^12} | {'LONGITUD':^12} | {'ALTITUD (m)':^14} |"
                    sep = "-" * len(header)
                    
                    print(sep)
                    print(header)
                    print(sep)
                    
                    for s_id, info in estaciones.items():
                        nombre = info.get('name', '--')[:25]
                        lat = info.get('latitude', '--')
                        lon = info.get('longitude', '--')
                        alt = info.get('altitude', '--')
                        
                        print(f"| {s_id:>8} | {nombre:>25} | {lat:>12} | {lon:>12} | {alt:>14} |")
                    print(sep)
                else:
                    print("[!] No hay estaciones activas configuradas.")
                
            elif sub == "2":
                print("\n[*] Conectando con AEMET para actualizar catálogo...")
                if data_manager.sync_stations():
                    print("[OK] Catálogo sincronizado correctamente.")
                else:
                    print("[ERROR] No se pudo sincronizar el catálogo con la API.")

            elif sub == 'X':
                break

            else:
                print("[!] Opción no reconocida.")
                input("\nPresione Enter para intentar de nuevo...")
                continue

            print("\n" + "="*95)
            if input("Quieres realizar otra gestión de estaciones? (s/n): ").lower().strip() != 's':
                break
        
        except KeyboardInterrupt:
            break

def option_configure_scheduler(scheduler):
    """
    Interface to manage the background automated data ingestion tasks.

    Displays the current status of the scheduler (Running/Stopped) and the 
    defined execution interval. Allows the user to start/stop the service 
    or modify the frequency of API checks.

    Args:
        scheduler (NimbusScheduler): The scheduler instance managing the 
                                     background threads and APScheduler logic.
    """
    while True:
        try:
            clear_screen()
            # Check for scheduled jobs to determine current status
            esta_corriendo = scheduler.scheduler.running
            state = "EJECUTÁNDOSE" if esta_corriendo else "PARADO"
            
            print("\n" + "="*60)
            print(f"--- [4] PLANIFICADOR DE INGESTA AUTOMÁTICA ---")
            print("="*60)
            print(f" ESTADO:    [{state}]")
            print(f" INTERVALO: Cada {scheduler.interval_minutes} minutos")
            print("-" * 60)
            print("[1] Iniciar Scheduler (Segundo plano)")
            print("[2] Detener Scheduler")
            print("[3] Cambiar intervalo de tiempo")
            print("[X] Volver al menú principal")
            print("-" * 60)

            opc = input("\nSeleccione una opción: ").strip().upper()

            if opc == "1":
                if not scheduler.scheduler.running:
                    scheduler.start()
                    print("[OK] El planificador se ha iniciado.")
                else:
                    print("[!] El planificador ya está en marcha.")
                input("Presione Enter para continuar...")

            elif opc == "2":
                if scheduler.scheduler.running:
                    scheduler.stop()
                    print("[OK] El planificador se ha detenido.")
                    # Re-instantiate if APScheduler does not allow restarting after shutdown
                else:
                    print("[!] El planificador ya está parado.")
                input("Presione Enter para continuar...")

            elif opc == "3":
                try:
                    minutos = int(input("\nNuevo intervalo (minutos): "))
                    if minutos < 1:
                        print("[!] El intervalo debe ser de al menos 1 minuto.")
                    else:
                        scheduler.update_interval(minutos)
                        print(f"[OK] Intervalo actualizado a {minutos} min.")
                except ValueError:
                    print("[!] Error: Ingrese un número válido.")
                input("Presione Enter para continuar...")

            elif opc == "X":
                break
        
        except KeyboardInterrupt:
            break

def main():
    config_logger()
    logger = logging.getLogger(__name__)
    logger.info("Iniciando Nimbus Data")

    config = ConfigManager()
    data_manager = DataManager(config)
    scheduler = NimbusScheduler(data_manager)
    alerts = AlertController()

    while True:
        try:
            clear_screen()
            choice = main_menu()
            if choice == "1": 
                clear_screen()
                option_automatic_ingestion(data_manager, alerts)
            elif choice == "2": 
                clear_screen()
                option_view_history(data_manager, alerts)
            elif choice == "3": 
                clear_screen()
                option_comparison_discrepancies(data_manager, alerts)
            elif choice == "4": 
                clear_screen()
                option_configure_scheduler(scheduler)
            elif choice == "5": 
                clear_screen()
                option_station_management(data_manager)
            elif choice.upper() == "X": 
                clear_screen()
                sys.exit(0)
        except KeyboardInterrupt: 
            sys.exit(0)

if __name__ == "__main__":
    main()
   