"""
Utility functions for error handling and retries.
"""

import asyncio
import logging
from typing import Any, Optional, Tuple, TypeVar, Callable, Awaitable
from datetime import datetime

from core.exceptions import RedisConnectionError, DatabaseError

logger = logging.getLogger(__name__)

# Utility functions for error handling and retries
T = TypeVar('T')

async def with_retries(
    func: Callable[[], Awaitable[T]], 
    max_retries: int = 3, 
    backoff_factor: float = 1.5,
    retry_exceptions: Tuple[Exception, ...] = (RedisConnectionError, DatabaseError)
) -> T:
    """Execute a function with exponential backoff retries
    
    Args:
        func: Async function to execute
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff
        retry_exceptions: Tuple of exceptions that should trigger a retry
        
    Returns:
        The return value of the function
        
    Raises:
        The last exception encountered if all retries fail
    """
    retries = 0
    last_exception = None
    
    while retries < max_retries:
        try:
            return await func()
        except retry_exceptions as e:
            retries += 1
            last_exception = e
            if retries >= max_retries:
                break
                
            # Exponential backoff
            wait_time = backoff_factor ** retries
            logger.warning(f"Retry {retries}/{max_retries} after {wait_time:.2f}s due to: {str(e)}")
            await asyncio.sleep(wait_time)
    
    # If we get here, all retries failed
    if last_exception:
        logger.error(f"All {max_retries} retries failed: {str(last_exception)}")
        raise last_exception
    
    # This should never happen, but just in case
    raise RuntimeError("Retry mechanism failed without an exception")

def log_error(error: Exception, context: Optional[dict] = None) -> None:
    """Log error with additional context
    
    Args:
        error: The exception to log
        context: Additional context information
    """
    error_data = {
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "timestamp": datetime.now().isoformat(),
    }
    
    if context:
        error_data.update(context)
        
    logger.error(f"Error: {error_data}")
