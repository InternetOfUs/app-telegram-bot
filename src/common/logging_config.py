import os


log_level = os.getenv("LOG_LEVEL", "INFO")
log_level_libraries = os.getenv("LOG_LEVEL_LIBS", "DEBUG")


def get_logging_configuration(service_name: str):
    """
    Get the logging configuration to be associated to a particular service.

    :param service_name: The name of the service (e.g. ws, backend, rule-engine, ..)
    :return: The logging configuration
    """
    log_on_file = "LOG_TO_FILE" in os.environ
    file_name = f"{service_name}.log"
    handlers = ["console"]
    if log_on_file:
        handlers.append("file")

    log_config = {
        "version": 1,
        "formatters": {
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": ""
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "simple",
                "level": "DEBUG",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": log_level,
            "handlers": handlers,
        },
        "loggers": {
            "werkzeug": {
                "level": log_level_libraries,
                "handlers": handlers,
                "propagate": 0
            },
            "uhopper": {
                "level": log_level,
                "handlers": handlers,
                "propagate": 0
            }
        }
    }
    if log_on_file:
        log_config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "simple",
            "filename": os.path.join(os.getenv("LOGS_DIR", ""), file_name),
            "maxBytes": 10485760,
            "backupCount": 3
        }

    return log_config
