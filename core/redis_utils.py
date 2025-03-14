"""
Redis utility functions for message buffering and processing.
"""

import json
import time
import logging
from typing import List, Optional, Dict, Any
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# Message buffering functions
async def add_message_to_buffer(redis: Redis, user_id: str, message_text: str) -> None:
    """Add a message to the user's buffer with timestamp"""
    message_data = {
        "text": message_text,
        "timestamp": time.time()
    }
    
    # Add message to the user's buffer
    buffer_key = f"user:{user_id}:buffer"
    
    # Use pipeline for atomic operations
    async with redis.pipeline() as pipe:
        await pipe.rpush(buffer_key, json.dumps(message_data))
        await pipe.expire(buffer_key, 300)  # 5 minutes expiry
        await pipe.execute()
    
    logger.info(f"Added message to buffer for user {user_id}: {message_text[:20]}...")

async def get_buffered_messages_without_clearing(redis: Redis, user_id: str) -> List[str]:
    """Retrieve messages from buffer without clearing it"""
    buffer_key = f"user:{user_id}:buffer"
    try:
        messages = await redis.lrange(buffer_key, 0, -1)
        return [json.loads(m)["text"] for m in messages if m]
    except Exception as e:
        logger.error(f"Buffer retrieval error: {str(e)}")
        return []

async def get_buffered_messages_with_timestamps(redis: Redis, user_id: str) -> List[Dict[str, Any]]:
    """Retrieve messages from buffer with their timestamps without clearing it"""
    buffer_key = f"user:{user_id}:buffer"
    try:
        messages = await redis.lrange(buffer_key, 0, -1)
        return [json.loads(m) for m in messages if m]
    except Exception as e:
        logger.error(f"Buffer retrieval error: {str(e)}")
        return []

async def clear_message_buffer(redis: Redis, user_id: str) -> None:
    """Clear the message buffer after processing"""
    buffer_key = f"user:{user_id}:buffer"
    await redis.delete(buffer_key)

async def get_buffered_messages(redis: Redis, user_id: str) -> List[str]:
    """Retrieve and clear messages (legacy method, use get_buffered_messages_without_clearing instead)"""
    buffer_key = f"user:{user_id}:buffer"
    try:
        # Get and clear in atomic transaction
        async with redis.pipeline(transaction=True) as pipe:
            await pipe.lrange(buffer_key, 0, -1)
            await pipe.delete(buffer_key)
            results = await pipe.execute()
        return [json.loads(m)["text"] for m in results[0] if m]
    except Exception as e:
        logger.error(f"Buffer retrieval error: {str(e)}")
        return []

async def is_buffer_active(redis: Redis, user_id: str) -> bool:
    """Check if there's an active processing flag for this user"""
    processing_key = f"user:{user_id}:processing"
    is_active = bool(await redis.exists(processing_key))
    if is_active:
        logger.info(f"Buffer is already being processed for user {user_id}")
    return is_active

async def set_buffer_processing(redis: Redis, user_id: str, timeout: int = 15) -> None:
    """Set processing flag with extended timeout"""
    await redis.setex(f"user:{user_id}:processing", timeout, "1")

async def schedule_processing(redis: Redis, user_id: str, delay_seconds: float) -> bool:
    """Schedule message processing for a user
    
    Args:
        redis: Redis connection
        user_id: Telegram user ID
        delay_seconds: Delay in seconds before processing
        
    Returns:
        bool: True if scheduled, False if already scheduled
    """
    scheduled_key = f"user:{user_id}:scheduled"
    
    # Try to set the scheduled flag (only succeeds if it doesn't exist)
    was_set = await redis.setnx(scheduled_key, str(time.time() + delay_seconds))
    
    if was_set:
        # Set expiry to ensure cleanup if processing fails
        await redis.expire(scheduled_key, int(delay_seconds * 2))
        logger.info(f"Scheduled processing for user {user_id} in {delay_seconds}s")
    else:
        logger.info(f"Processing already scheduled for user {user_id}")
        
    return bool(was_set)

async def is_processing_scheduled(redis: Redis, user_id: str) -> bool:
    """Check if processing is scheduled for a user
    
    Args:
        redis: Redis connection
        user_id: Telegram user ID
        
    Returns:
        bool: True if processing is scheduled
    """
    scheduled_key = f"user:{user_id}:scheduled"
    return bool(await redis.exists(scheduled_key))

async def clear_processing_schedule(redis: Redis, user_id: str) -> None:
    """Clear the processing schedule flag
    
    Args:
        redis: Redis connection
        user_id: Telegram user ID
    """
    scheduled_key = f"user:{user_id}:scheduled"
    await redis.delete(scheduled_key)
    logger.info(f"Cleared processing schedule for user {user_id}")

async def get_last_processed_time(redis: Redis, user_id: str) -> float:
    """Get the timestamp when messages were last processed for a user
    
    Args:
        redis: Redis connection
        user_id: Telegram user ID
        
    Returns:
        float: Timestamp of last processing, or 0 if never processed
    """
    last_processed_key = f"user:{user_id}:last_processed"
    timestamp = await redis.get(last_processed_key)
    return float(timestamp) if timestamp else 0

async def set_last_processed_time(redis: Redis, user_id: str, timestamp: float = None) -> None:
    """Set the timestamp when messages were last processed for a user
    
    Args:
        redis: Redis connection
        user_id: Telegram user ID
        timestamp: Timestamp to set, defaults to current time
    """
    last_processed_key = f"user:{user_id}:last_processed"
    await redis.set(last_processed_key, str(timestamp or time.time()))

# Rate limiting for LLM calls
async def check_llm_rate_limit(redis: Redis, user_id: str, llm_calls_per_minute: int = 5, window_seconds: int = 60) -> Optional[str]:
    """Check if user has exceeded LLM call rate limits
    
    Args:
        redis: Redis connection
        user_id: User identifier
        llm_calls_per_minute: Maximum number of LLM calls allowed per minute
        window_seconds: Time window for rate limiting in seconds
        
    Returns:
        Optional[str]: Error message if rate limited, None otherwise
    """
    if not redis:
        return None  # No Redis connection, skip rate limiting
        
    # Increment counter for this user's LLM calls
    key = f"rate:llm:{user_id}"
    count = await redis.incr(key)
    
    # Set expiry on first request
    if count == 1:
        await redis.expire(key, window_seconds)
    
    # Check if over limit
    if count > llm_calls_per_minute:
        return f"You've sent too many messages. Please wait a moment before sending more."
    
    return None
