"""
Core bot framework package.
"""

from core.exceptions import (
    BotError,
    RedisConnectionError,
    LockAcquisitionError,
    MessageProcessingError,
    AgentInvocationError,
    RateLimitError,
    DatabaseError,
    ConfigurationError,
    TelegramAPIError
)

from core.utils import with_retries, log_error
from core.message_handler import MessageProcessor, TypingIndicator

__all__ = [
    # Exceptions
    'BotError',
    'RedisConnectionError',
    'LockAcquisitionError',
    'MessageProcessingError',
    'AgentInvocationError',
    'RateLimitError',
    'DatabaseError',
    'ConfigurationError',
    'TelegramAPIError',
    
    # Utilities
    'with_retries',
    'log_error',
    
    # Message handling
    'MessageProcessor',
    'TypingIndicator'
]
