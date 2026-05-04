import os
import sys
import logging
import platform
import subprocess
from datetime import datetime

# Configuracion basica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.utils.config_manager import ConfigManager
from src.processing.data_manager import DataManager
from src.storage import json_handler
from src.utils.scheduler import NimbusScheduler


# Funciones de validación de fechas

def solicitar_fecha_inicio(hoy_str: str, hoy_dt: datetime) -> datetime:
    """Solicita y valida que la fecha de inicio no sea futura y tenga formato correcto."""
    while True:
        entrada = input(f"Fecha Inicio (YYYY-MM-DD) [[Enter] hoy: {hoy_str}]: ").strip() or hoy_str
        try:
            fecha_dt = datetime.strptime(entrada, "%Y-%m-%d")
            if fecha_dt > hoy_dt:
                print(f"[!] Error: La fecha de inicio no puede ser futura.")
                continue
            return fecha_dt
        except ValueError:
            print("[!] Error: Formato incorrecto. Use YYYY-MM-DD (ej: 2024-03-15).")

def solicitar_fecha_fin(inicio_dt: datetime, hoy_dt: datetime, hoy_str: str) -> datetime:
    """Solicita y valida que la fecha fin no sea futura y sea igual o posterior al inicio."""
    while True:
        entrada = input(f"Fecha Fin    (YYYY-MM-DD) [[Enter] hoy: {hoy_str}]: ").strip() or hoy_str
        try:
            fecha_dt = datetime.strptime(entrada, "%Y-%m-%d")
            if fecha_dt > hoy_dt:
                print(f"[!] Error: La fecha fin no puede ser futura.")
                continue
            if fecha_dt < inicio_dt:
                print(f"[!] Error: La fecha fin debe ser igual o posterior a la fecha de inicio ({inicio_dt.strftime('%Y-%m-%d')}).")
                continue
            return fecha_dt
        except ValueError:
            print("[!] Error: Formato incorrecto. Use YYYY-MM-DD.")

# Funciones de interfaz

def limpiar_pantalla():
    try:
        print("\033[H\033[2J", end="", flush=True)
        es_windows = platform.system() == "Windows"
        comando = "cls" if es_windows else "clear"
        subprocess.run(comando, shell=es_windows, check=True)
    except Exception:
        print("\033[H\033[2J", end="")

def menu_principal():
    print("\n" + "="*50)
    print("NIMBUS DATA")
    print("="*50)
    print("[1] Ingesta Automática (AEMET)")
    print("[2] Ver Historico de Datos")
    print("[3] Comparativa de fuentes")
    print("[4] Configurar Scheduler")
    print("[5] Gestión de Estaciones")
    print("[X] Salir")
    print("\n(Ctrl+C para Salir del programa)")
    return input("Selecciona una opción: ").strip()

def seleccionar_estaciones(data_manager, active=True):
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

# Lógica de opciones

def opcion_ingesta_automatica(data_manager):
    while True:
        try:
            print("\n" + "="*70)
            print("--- [1] INGESTA MANUAL (Sincronización API AEMET) ---")
            print("="*70)

            target_stations = seleccionar_estaciones(data_manager)
            if not target_stations: break

            hoy_dt = datetime.now()
            hoy_str = hoy_dt.strftime("%Y-%m-%d")
            
            dt_ini = solicitar_fecha_inicio(hoy_str, hoy_dt)
            dt_fin = solicitar_fecha_fin(dt_ini, hoy_dt, hoy_str)
            start, end = dt_ini.strftime("%Y-%m-%d"), dt_fin.strftime("%Y-%m-%d")

            for s_id, s_name in target_stations:
                print(f"\n[API] Descargando: {s_name} ({s_id})...")
                nuevos = data_manager.force_api_ingest(start, end, s_id)

                if nuevos:
                    # Definición de cabecera y separador dinámico
                    header = f"| {'FECHA':^12} | {'TEMPERATURA (C)':^19} | {'HUMEDAD (%)':^12} | {'VELOCIDAD (km/h)':^18} |"
                    separator = "-" * len(header)
                    print(separator)
                    print(header)
                    print(separator)

                    for r in nuevos:
                        # Acceso a atributos del objeto WeatherRecord
                        f_clean = r.date.split('T')[0] if r.date else "--"
                        t = f"{r.temp_avg:.1f}" if r.temp_avg is not None else "--"
                        h = f"{r.humidity_avg}" if r.humidity_avg is not None else "--"
                        v = f"{r.wind_speed_avg:.1f}" if r.wind_speed_avg is not None else "--"
                        
                        print(f"| {f_clean:^12} | {t:^19} | {h:^12} | {v:^18} |")
                    print(separator)
                else:
                    print(f"[!] No se recibieron datos para {s_name}.")

            if input("\n¿Desea realizar otra sincronización? (s/n): ").lower() != 's': 
                break

        except KeyboardInterrupt: 
            break

def opcion_ver_historico(data_manager):
    while True:
        try:
            limpiar_pantalla()
            print("\n--- [2] CONSULTA DE HISTÓRICO ---")
            target_stations = seleccionar_estaciones(data_manager)
            if not target_stations: return 

            hoy_dt = datetime.now()
            hoy_str = hoy_dt.strftime("%Y-%m-%d")

            # Validation
            dt_ini = solicitar_fecha_inicio(hoy_str, hoy_dt)
            dt_fin = solicitar_fecha_fin(dt_ini, hoy_dt, hoy_str)
            
            start, end = dt_ini.strftime("%Y-%m-%d"), dt_fin.strftime("%Y-%m-%d")

            for s_id, s_name in target_stations:
                records = data_manager.get_weather(start, end, s_id)
                if records:
                    print(f"\nESTACIÓN: {s_name.upper()}\n")
                    header = f"| {'FECHA':^12} | {'TEMPERATURA (C)':^19} | {'HUMEMDAD (%)':^12} | {'VELOCIDAD (km/h)':^18} |"
                    separator = "-" * len(header)
                    print(separator) 
                    print(header)
                    print(separator) 
                    for r in records:
                        print(f"| {r.get('date','--').split('T')[0]:^12} | "
                            f"{str(r.get('temp_avg','--')):^19} | "
                            f"{str(r.get('humidity_avg','--')):^12} | "
                            f"{str(r.get('wind_speed_avg','--')):^18} | "
                        )
                    print(separator)
            
            if input("\n¿Quieres hacer otra consulta? (s/n): ").lower() != 's': break
        
        except KeyboardInterrupt:
            break

def opcion_comparativa_discrepancias(data_manager):
    while True:
        try:
            limpiar_pantalla()
            print("\n--- [3] COMPARATIVA Y DISCREPANCIAS ---")
            resultado = seleccionar_estaciones(data_manager)
            if not resultado: break 
            
            s_id, s_name = resultado[0]
            hoy_dt = datetime.now()
            hoy_str = hoy_dt.strftime("%Y-%m-%d")

            # Validation
            dt_ini = solicitar_fecha_inicio(hoy_str, hoy_dt)
            dt_fin = solicitar_fecha_fin(dt_ini, hoy_dt, hoy_str)
            
            start, end = dt_ini.strftime("%Y-%m-%d"), dt_fin.strftime("%Y-%m-%d")

            # Obtención de datos
            local_h = data_manager.get_records_from_json(start, end, s_id)
            records_json = {r['date'].split('T')[0]: r for r in local_h}
            api_h = data_manager.force_api_ingest(start, end, s_id)
            records_api = {r.date.split('T')[0]: r for r in api_h}

            todas_las_fechas = sorted(set(records_json.keys()) | set(records_api.keys()))

            w_fecha, w_sub, w_status = 12, 8, 18
            w_main = (w_sub * 2) + 3 
            header_l1 = (f"{'':^{w_fecha}} | {'TEMPERATURA':^{w_main}} | "
                        f"{'HUMEDAD':^{w_main}} | {'VIENTO':^{w_main}} | {'ESTADO':^{w_status}}")
            header_l2 = (f"{'FECHA':^{w_fecha}} | {'JSON':^{w_sub}} | {'API':^{w_sub}} | "
                        f"{'JSON':^{w_sub}} | {'API':^{w_sub}} | "
                        f"{'JSON':^{w_sub}} | {'API':^{w_sub}} | {'':^{w_status}}")

            print("\n" + header_l1 + "\n" + header_l2 + "\n" + "-" * len(header_l2))

            def fmt(val):
                if val is None or val == '--': return "--"
                try: return f"{float(val):.1f}"
                except: return "--"

            for f in todas_las_fechas:
                rj, ra = records_json.get(f, {}), records_api.get(f)
                tj, hj, vj = fmt(rj.get('temp_avg')), fmt(rj.get('humidity_avg')), fmt(rj.get('wind_speed_avg'))
                ta, ha, va = fmt(getattr(ra, 'temp_avg', None)), fmt(getattr(ra, 'humidity_avg', None)), fmt(getattr(ra, 'wind_speed_avg', None))

                status = "OK"
                json_vacio, api_vacia = all(v=="--" for v in [tj,hj,vj]), all(v=="--" for v in [ta,ha,va])
                
                if json_vacio and api_vacia: status = "--"
                elif not json_vacio and api_vacia: status = "--"
                elif json_vacio and not api_vacia: status = "NUEVO REGISTRO"
                else:
                    if any(abs(float(v1)-float(v2)) > 0.01 for v1, v2 in [(tj,ta),(hj,ha),(vj,va)] if v1!="--" and v2!="--"):
                        status = "KO"

                print(f"{f:^{w_fecha}} | {tj:^{w_sub}} | {ta:^{w_sub}} | {hj:^{w_sub}} | {ha:^{w_sub}} | {vj:^{w_sub}} | {va:^{w_sub}} | {status:^{w_status}}")

            if input("\n¿Quieres hacer otra comparación? (s/n): ").lower() != 's': break
        
        except KeyboardInterrupt:
            break

def opcion_gestion_estaciones(data_manager):
    while True:
        try:
            limpiar_pantalla()
            print("\n" + "="*95)
            print("--- [5] GESTIÓN DE ESTACIONES ---")
            print("="*95)
            print("[1] Ver estaciones activas (Detalles Técnicos)")
            print("[2] Sincronizar catálogo con AEMET")
            print("[X] Volver al menú principal")
            print("="*95)
            
            sub = input("\nSelecciona una opción: ").strip().upper()

            if sub == "1":
                print("\n[ESTACIONES ACTIVAS - DETALLES]")
                estaciones = data_manager.get_active_stations_info()
                
                if estaciones:
                    # Configuración de la tabla
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

def opcion_configurar_scheduler(scheduler):
    while True:
        limpiar_pantalla()
        # Verifica si hay trabajos programados para determinar el estado
        esta_corriendo = scheduler.scheduler.running
        estado = "EJECUTÁNDOSE" if esta_corriendo else "PARADO"
        
        print("\n" + "="*60)
        print(f"--- [4] PLANIFICADOR DE INGESTA AUTOMÁTICA ---")
        print("="*60)
        print(f" ESTADO:    [{estado}]")
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
                # Re-instancia si APScheduler no permite reiniciar tras shutdown
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

def main():
    config = ConfigManager()
    data_manager = DataManager(config)
    scheduler = NimbusScheduler(data_manager)

    while True:
        try:
            limpiar_pantalla()
            choice = menu_principal()
            if choice == "1": 
                limpiar_pantalla()
                opcion_ingesta_automatica(data_manager)
            elif choice == "2": 
                limpiar_pantalla()
                opcion_ver_historico(data_manager)
            elif choice == "3": 
                limpiar_pantalla()
                opcion_comparativa_discrepancias(data_manager)
            elif choice == "4": 
                limpiar_pantalla()
                opcion_configurar_scheduler(scheduler)
            elif choice == "5": 
                limpiar_pantalla()
                opcion_gestion_estaciones(data_manager)
            elif choice.upper() == "X": 
                limpiar_pantalla()
                sys.exit(0)
        except KeyboardInterrupt: 
            sys.exit(0)

if __name__ == "__main__":
    main()
   