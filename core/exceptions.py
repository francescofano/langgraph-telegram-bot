"""
Core exception classes for the bot framework.
"""

class BotError(Exception):
    """Base class for bot-specific errors"""
    def __init__(self, message: str = "An error occurred in the bot"):
        self.message = message
        super().__init__(self.message)

class RedisConnectionError(BotError):
    """Raised when Redis connection fails or times out"""
    def __init__(self, message: str = "Failed to connect to Redis"):
        super().__init__(message)

class LockAcquisitionError(BotError):
    """Raised when lock acquisition fails or times out"""
    def __init__(self, message: str = "Failed to acquire lock"):
        super().__init__(message)

class MessageProcessingError(BotError):
    """Raised when message processing fails"""
    def __init__(self, message: str = "Failed to process message"):
        super().__init__(message)

class AgentInvocationError(BotError):
    """Raised when LLM/agent invocation fails"""
    def __init__(self, message: str = "Failed to invoke AI agent"):
        super().__init__(message)

class RateLimitError(BotError):
    """Raised when rate limits are exceeded"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message)

class DatabaseError(BotError):
    """Raised when database operations fail"""
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message)

class ConfigurationError(BotError):
    """Raised when configuration is missing or invalid"""
    def __init__(self, message: str = "Invalid or missing configuration"):
        super().__init__(message)

class TelegramAPIError(BotError):
    """Raised when Telegram API calls fail"""
    def __init__(self, message: str = "Telegram API error"):
        super().__init__(message)
