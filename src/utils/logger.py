import logging
import os

def config_logger(name="nimbus_logger", log_file="logs/app.log", level=logging.INFO):
 
    # 1. Create logger first to avoid multiple handlers if called multiple times
    logger = logging.getLogger(name)
    logger.setLevel(level)   

    # 2. Avoid duplicating handlers if they are called multiple times
    if logger.handlers:
        return logger

    # 3. Create log directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # 4. Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )
    
     # 5. Handlers
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 6. Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Initialize the logger
_logger = config_logger()

def log_info(message):
    _logger.info(message)

def log_error(message):
    _logger.error(message)

def log_warning(message):   
    _logger.warning(message)