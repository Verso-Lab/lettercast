import logging
import json
import traceback
from datetime import datetime

def setup_lambda_logging():
    """Configure logging for AWS Lambda environment"""
    # Remove any existing handlers
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)
    
    # Set up basic configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create a JSON formatter for structured logging
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
            }
            
            if record.exc_info:
                log_record['exception'] = {
                    'type': record.exc_info[0].__name__,
                    'message': str(record.exc_info[1]),
                    'traceback': traceback.format_exception(*record.exc_info)
                }
            
            return json.dumps(log_record)
    
    # Create and add handler with JSON formatter
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    
    return logging.getLogger(__name__)

def get_logger(name):
    """Get a logger instance with the specified name"""
    return logging.getLogger(name) 