"""
Base configuration settings.
"""

import os
import dotenv
import logging
from dataclasses import dataclass

# Load environment variables
dotenv.load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, log_level, logging.INFO)
)
logger = logging.getLogger(__name__)
logger.info(f"Starting with log level: {log_level}")

@dataclass
class BaseConfig:
    """Base configuration settings loaded from environment variables"""
    pg_connection: str = os.getenv("PG_CONNECTION_STRING")
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
