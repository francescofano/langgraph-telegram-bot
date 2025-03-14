"""
Bot-specific configuration settings.
"""

import os
from dataclasses import dataclass
from config.base_config import BaseConfig

@dataclass
class BotConfig(BaseConfig):
    """Bot-specific configuration settings loaded from environment variables"""
    telegram_token: str = os.getenv("TELEGRAM_TOKEN")
    debounce_time: float = float(os.getenv("DEBOUNCE_TIME", "5.0"))
    llm_calls_per_minute: int = int(os.getenv("LLM_CALLS_PER_MINUTE", "5"))
