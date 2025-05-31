import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(service_name: str, log_dir: str = "/logs", level=logging.INFO):
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(service_name)
    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )

    file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, f"{service_name}.log"),
        maxBytes=10*1024*1024,
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
