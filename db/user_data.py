"""
User data management utilities.
"""

import logging
from typing import Optional
from redis.asyncio import Redis
from psycopg_pool import AsyncConnectionPool
from langgraph.store.postgres import AsyncPostgresStore

logger = logging.getLogger(__name__)

async def clear_user_data(
    user_id: str, 
    redis: Redis, 
    pool: AsyncConnectionPool, 
    store: AsyncPostgresStore
) -> None:
    """Clear all data for a user to start fresh
    
    Args:
        user_id: User identifier
        redis: Redis connection
        pool: PostgreSQL connection pool
        store: Vector store (optional)
    """
    # TODO: Implement user data clearing functionality
    # This should:
    # 1. Clear Redis data for the user
    # 2. Clear PostgreSQL data (langgraph_checkpoints)
    # 3. Clear vector memories if store is provided
    
    # 1. Clear Redis data - delete keys with pattern matching user_id
    user_keys = await redis.keys(f"user:{user_id}:*")
    if user_keys:
        await redis.delete(*user_keys)
        logger.info(f"Cleared {len(user_keys)} Redis keys for user {user_id}")    
        


    # 2. Clear PostgreSQL data (langgraph_checkpoints)
    try:
        async with pool.connection() as conn:
            result = await conn.execute(
                "DELETE FROM checkpoints WHERE thread_id = %s",
                (user_id,)
            )
            logger.info(f"Cleared PostgreSQL checkpoints for user {user_id}")
    except Exception as e:
        logger.error(f"Error clearing PostgreSQL data: {str(e)}")
    
      
    try:
        # Delete memories with user_id as namespace
        try:
            # Delete with user_id as namespace (new format)
            namespace = (str(user_id),)
            
            # Use direct SQL queries to delete from both tables
            async with pool.connection() as conn:
                # Delete from store table
                result = await conn.execute(
                    """
                    DELETE FROM store 
                    WHERE prefix = %s
                    """,
                    (str(user_id),)
                )
                store_deleted = result.rowcount
                logger.info(f"Deleted {store_deleted} rows from store table for user {user_id}")
                
                # Delete from store_vector table
                result = await conn.execute(
                    """
                    DELETE FROM store_vectors
                    WHERE prefix = %s
                    """,
                    (str(user_id),)
                )
                vector_deleted = result.rowcount
                logger.info(f"Deleted {vector_deleted} rows from store_vector table for user {user_id}")
                
                logger.info(f"Successfully deleted all memories for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error deleting memories with namespace={user_id}: {str(e)}")
            
        # Also try to delete from the old "memories" namespace for backward compatibility
        try:
            old_namespace = ("memories",)
            await store.adelete(old_namespace, user_id)
            logger.info(f"Deleted memory with namespace=memories, key={user_id}")
        except Exception as e:
            logger.debug(f"No memories found in old format (namespace=memories, key={user_id}): {str(e)}")
            
    except Exception as e:
        logger.error(f"Error clearing vector memories: {str(e)}")
    
    logger.info(f"Completed data clearing for user {user_id}")
