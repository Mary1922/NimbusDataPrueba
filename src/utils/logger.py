import logging
import os

def config_logger(name="nimbus_logger", log_file="logs/app.log", level=logging.INFO):
    # Asegurar que la carpeta logs existe
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Evitar duplicar handlers si se llama varias veces
    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

# Inicialización
_logger = config_logger()

def log_info(message):
    _logger.info(message)

def log_error(message):
    _logger.error(message)

def log_warning(message):   
    _logger.warning(message)