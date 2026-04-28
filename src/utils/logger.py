import logging
import os

def config_logger(name="nimbus_logger", log_file="logs/app.log", level=logging.INFO):
    """
    Configura y devuelve un logger reutilizable.
    """

    # Evitar duplicar logs
    if logger.handlers:
        return logger

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


# Helpers seguros
_logger = config_logger()

def log_info(message):
    _logger.info(message)

def log_error(message):
    _logger.error(message)