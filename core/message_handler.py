"""
Core message processing functionality with debouncing and rate limiting.
"""

import asyncio
import time
import logging
from typing import Any, Callable, Awaitable, List, Dict, Optional

from redis.asyncio import Redis

from core.exceptions import RedisConnectionError, RateLimitError
from core.utils import with_retries, log_error
from core.redis_utils import (
    add_message_to_buffer,
    get_buffered_messages_with_timestamps,
    clear_message_buffer,
    schedule_processing,
    is_processing_scheduled,
    clear_processing_schedule,
    get_last_processed_time,
    set_last_processed_time,
    set_buffer_processing,
    check_llm_rate_limit
)

logger = logging.getLogger(__name__)

class TypingIndicator:
    """Base class for typing indicators"""
    
    @staticmethod
    async def send_periodically(chat_id: Any) -> None:
        """
        Send typing action periodically
        This is a placeholder that should be overridden by platform-specific implementations
        """
        pass

    class ContextManager:
        """Context manager for continuous typing indicator"""
        def __init__(self, chat_id: Any):
            self.chat_id = chat_id
            self.task = None

        async def __aenter__(self):
            # This should be overridden by platform-specific implementations
            return self

        async def __aexit__(self, exc_type, exc, tb):
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass

class MessageProcessor:
    """Handles processing of user messages with debouncing and rate limiting"""
    
    def __init__(self, redis: Redis, debounce_time: float = 2.0, 
                 llm_calls_per_minute: int = 5, window_seconds: int = 60):
        """Initialize the message processor
        
        Args:
            redis: Redis connection
            debounce_time: Time to wait for additional messages (seconds)
            llm_calls_per_minute: Maximum number of LLM calls allowed per minute
            window_seconds: Time window for rate limiting in seconds
        """
        self.redis = redis
        self.debounce_time = debounce_time
        self.llm_calls_per_minute = llm_calls_per_minute
        self.window_seconds = window_seconds
    
    async def acquire_user_lock(self, user_id: str, timeout: int = 30, 
                               blocking: bool = True,
                               blocking_timeout: int = 5) -> tuple[bool, Any]:
        """Acquire a lock for processing user messages
        
        Args:
            user_id: User identifier
            timeout: Lock timeout in seconds
            blocking: Whether to block waiting for the lock
            blocking_timeout: Maximum time to wait for lock acquisition
            
        Returns:
            Tuple of (acquired status, lock object)
        
        Raises:
            LockAcquisitionError: If lock acquisition fails
        """
        lock_key = f"user:{user_id}:lock"
        try:
            lock = self.redis.lock(lock_key, timeout=timeout)
            acquired = await lock.acquire(blocking=blocking, blocking_timeout=blocking_timeout)
            return acquired, lock
        except Exception as e:
            log_error(e, {"user_id": user_id, "operation": "lock_acquisition"})
            raise RedisConnectionError(f"Failed to acquire lock: {str(e)}")
    
    async def perform_debounce(self, user_id: str) -> None:
        """Wait for additional messages during debounce period
        
        Args:
            user_id: User identifier
            
        Raises:
            RedisConnectionError: If Redis operations fail
        """
        try:
            # Just wait for the debounce period to allow more messages to arrive
            logger.info(f"Waiting for {self.debounce_time}s to collect more messages for {user_id}")
            await asyncio.sleep(self.debounce_time)
        except Exception as e:
            log_error(e, {"user_id": user_id, "operation": "perform_debounce"})
            raise
    
    async def handle_message(
        self, 
        user_id: str, 
        message_text: str,
        response_callback: Optional[Callable[[str, Any], Awaitable[None]]] = None,
        typing_indicator_callback: Optional[Callable[[str, bool], Awaitable[None]]] = None
    ) -> None:
        """Handle incoming messages by adding to buffer and scheduling delayed processing
        
        Args:
            user_id: User identifier
            message_text: The message content
            response_callback: Optional callback function to send response back to the user
            typing_indicator_callback: Optional callback to manage typing indicator
        """
        if not self.redis:
            logger.error("Redis connection not available")
            raise RedisConnectionError("Redis connection not available")
        
        # Always add the message to buffer first
        try:
            await with_retries(
                lambda: add_message_to_buffer(self.redis, user_id, message_text)
            )
            logger.info(f"Added message to buffer for {user_id}: {message_text[:20]}...")
        except Exception as e:
            log_error(e, {"user_id": user_id, "operation": "add_to_buffer"})
            raise
        
        # Check if processing is already scheduled for this user
        is_scheduled = await with_retries(
            lambda: is_processing_scheduled(self.redis, user_id)
        )
        
        if is_scheduled:
            # Processing is already scheduled, nothing more to do
            logger.info(f"Processing already scheduled for {user_id}, message added to buffer")
            return
        
        # Schedule processing after debounce period
        scheduled = await with_retries(
            lambda: schedule_processing(self.redis, user_id, self.debounce_time)
        )
        
        if scheduled:
            # Create a task to process messages after debounce period
            # This runs independently and doesn't block the current handler
            asyncio.create_task(
                self.process_messages_after_delay(
                    user_id=user_id,
                    delay=self.debounce_time,
                    response_callback=response_callback,
                    typing_indicator_callback=typing_indicator_callback
                )
            )
            logger.info(f"Scheduled message processing for {user_id} in {self.debounce_time}s")
    
    async def process_messages_after_delay(
        self, 
        user_id: str,
        delay: float,
        response_callback: Optional[Callable[[str, Any], Awaitable[None]]] = None,
        typing_indicator_callback: Optional[Callable[[str, bool], Awaitable[None]]] = None
    ) -> None:
        """Process messages after a delay to allow for message batching
        
        Args:
            user_id: User identifier
            delay: Delay in seconds before processing
            response_callback: Optional callback function to send response back to the user
            typing_indicator_callback: Optional callback to manage typing indicator
        """
        processing_key = f"user:{user_id}:processing"
        
        try:
            # Wait for the specified delay
            await asyncio.sleep(delay)
            
            # Set processing flag to prevent other processes from handling
            await with_retries(
                lambda: set_buffer_processing(self.redis, user_id, int(delay * 2))
            )
            
            # Get messages with timestamps
            messages_with_timestamps = await with_retries(
                lambda: get_buffered_messages_with_timestamps(self.redis, user_id)
            )
            
            if not messages_with_timestamps:
                logger.info(f"No messages to process for {user_id}")
                return
                
            # Get the last processed time
            last_processed = await with_retries(
                lambda: get_last_processed_time(self.redis, user_id)
            )
            
            # Filter messages that arrived after the last processing time
            new_messages = [
                msg for msg in messages_with_timestamps
                if msg["timestamp"] > last_processed
            ]
            
            if not new_messages:
                logger.info(f"No new messages to process for {user_id}")
                return
                
            # Extract just the text from messages
            message_texts = [msg["text"] for msg in new_messages]
            logger.info(f"Processing {len(message_texts)} messages for {user_id}")
            
            # Check rate limit
            rate_error = await check_llm_rate_limit(
                self.redis, 
                user_id, 
                self.llm_calls_per_minute, 
                self.window_seconds
            )
            
            if rate_error:
                raise RateLimitError(rate_error)
            
            # Start typing indicator if callback provided
            if typing_indicator_callback:
                logger.info(f"Starting typing indicator for user {user_id}")
                await typing_indicator_callback(user_id, True)
            
            try:
                # Process messages - this should be implemented by subclasses
                result = await self.process_messages(user_id, message_texts)
                
                # Call the response callback if provided
                if response_callback:
                    logger.info(f"Sending response to user {user_id}")
                    await response_callback(user_id, result)
                else:
                    logger.warning(f"No response callback provided for user {user_id}")
            finally:
                # Stop typing indicator if callback provided
                if typing_indicator_callback:
                    logger.info(f"Stopping typing indicator for user {user_id}")
                    await typing_indicator_callback(user_id, False)
            
            # Update the last processed time
            current_time = time.time()
            await with_retries(
                lambda: set_last_processed_time(self.redis, user_id, current_time)
            )
            
            # Clear buffer AFTER successful processing
            await with_retries(
                lambda: clear_message_buffer(self.redis, user_id)
            )
            logger.info(f"Cleared buffer for {user_id} after processing")
                
        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded for user {user_id}: {str(e)}")
            # This should be handled by the platform-specific implementation
            raise
        except Exception as e:
            log_error(e, {"user_id": user_id, "operation": "process_messages_after_delay"})
            raise
        finally:
            # Always clear the flags when done
            try:
                # Clear processing flag
                await self.redis.delete(processing_key)
                # Clear scheduled flag
                await with_retries(
                    lambda: clear_processing_schedule(self.redis, user_id)
                )
                logger.info(f"Cleared processing flags for {user_id}")
            except Exception as e:
                log_error(e, {"user_id": user_id, "operation": "cleanup_flags"})
    
    async def process_messages(self, user_id: str, messages: List[str]) -> Any:
        """
        Process the aggregated messages and generate a response
        This method should be overridden by subclasses to implement specific processing logic
        
        Args:
            user_id: User identifier
            messages: List of messages to process
            
        Returns:
            The processing result (implementation-specific)
        """
        raise NotImplementedError("Subclasses must implement process_messages")
