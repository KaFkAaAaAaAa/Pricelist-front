LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
    "json": {
        "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
        "datefmt": "%Y-%m-%dT%H:%M:%SZ",
    },
    "base": {
        "format": "%(asctime)s [%(levelname)s] :: %(message)s - at %(name)s",
        "datefmt": "%Y-%m-%dT%H:%M:%SZ",
    },
},

    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "base",
            "level": "INFO",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "pricelist-front.log",
            "formatter": "json",
            "level": "DEBUG",
        },
    },
    "loggers": {"": {"handlers": ["stdout", "file"], "level": "INFO"}},
}
