import logging
import sys
import config

def setup_logger(name=__name__):
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        
        # Set format
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        
        # Set level based on config
        if config.ENABLE_DEBUG_LOGS:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.ERROR) # Only show errors and critical info by default
            
    return logger

def get_logger(name):
    return logging.getLogger(name)
