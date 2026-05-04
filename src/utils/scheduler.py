import logging
from datetime import datetime
from typing import Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

class NimbusScheduler:
    """
    Background scheduler service using APScheduler.
    Handles automated data ingestion cycles without blocking the UI.
    """
    def __init__(self, bridge: Any) -> None:
        self.bridge = bridge
        self.logger = logging.getLogger("Nimbus.Scheduler")
        
        # BackgroundScheduler runs in a separate thread
        self.scheduler = BackgroundScheduler(daemon=True)
        self.job_id = 'nimbus_auto_sync_job'
        
        # Initial interval from configuration
        self.interval_minutes = self.bridge.dm.config.get("settings.interval_minutes", 30)
        
        # Job registration
        self.scheduler.add_job(
            func=self._execute_ingestion_job,
            trigger=IntervalTrigger(minutes=self.interval_minutes),
            id=self.job_id,
            name='Automated AEMET Sync Task',
            replace_existing=True
        )

    def start(self) -> None:
        """Starts the background scheduler service."""
        if not self.scheduler.running:
            self.scheduler.start()
            self.logger.info(f"Scheduler iniciado. Intervalos de : {self.interval_minutes} min.")

    def stop(self) -> None:
        """Shuts down the scheduler service."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.logger.info("Scheduler parado.")

    def update_interval(self, minutes: int) -> None:
        """
        Dynamically updates the execution frequency of the sync job.
        """
        if minutes < 1: 
            minutes = 1
            
        self.interval_minutes = minutes
        
        if self.scheduler.get_job(self.job_id):
            self.scheduler.reschedule_job(
                self.job_id, 
                trigger=IntervalTrigger(minutes=self.interval_minutes)
            )
            self.logger.info(f"Intervalo de ejecución reprogramado a {minutes} min.")

    def _execute_ingestion_job(self) -> None:
        """
        Internal worker that pulls data for all active stations.
        """
        self.logger.info("Inicio de ciclo de ingestión programado...")
        try:
            # Type hinting the expected return list of tuples (id, name)
            stations = self.bridge.obtener_lista_estaciones(activas=True)
            today_str = datetime.now().strftime("%Y-%m-%d")

            for s_id, s_name in stations:
                # Calls the logic bridge to handle the API pull and persistence
                self.bridge.ejecutar_ingesta_forzada(today_str, today_str, s_id)
            
            self.logger.info("Cliclo de ingestión programado completado con éxito.")
        except Exception as e:
            self.logger.error(f"Error durante la ejecución de la tarea programada: {e}")