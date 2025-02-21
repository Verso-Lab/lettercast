import logging
import logging.config
import json
import traceback
from datetime import datetime, timezone

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        if record.exc_info:
            log_record['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': ''.join(traceback.format_exception(*record.exc_info)),
            }
        return json.dumps(log_record)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": JsonFormatter
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "level": "INFO",
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    }
}

def setup_logging(level: str = "INFO"):
    LOGGING_CONFIG["handlers"]["console"]["level"] = level
    LOGGING_CONFIG["root"]["level"] = level
    logging.config.dictConfig(LOGGING_CONFIG)
    return logging.getLogger(__name__)
