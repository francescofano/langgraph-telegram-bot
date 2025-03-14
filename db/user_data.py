"""
User data management utilities.
"""

import logging
from typing import Optional, List, Dict, Any
from redis.asyncio import Redis
from psycopg_pool import AsyncConnectionPool
from langgraph.store.postgres import AsyncPostgresStore

logger = logging.getLogger(__name__)

async def clear_user_data(
    user_id: str, 
    redis: Redis, 
    pool: AsyncConnectionPool, 
    store: Optional[AsyncPostgresStore] = None
) -> None:
    """Clear all data for a user to start fresh
    
    Args:
        user_id: User identifier
        redis: Redis connection
        pool: PostgreSQL connection pool
        store: Vector store (optional)
    """
    # 1. Clear Redis data
    redis_keys = [
        f"user:{user_id}:buffer",
        f"user:{user_id}:processing",
        f"user:{user_id}:scheduled",
        f"user:{user_id}:last_processed",
        f"user:{user_id}:lock",
        f"rate:llm:{user_id}"
    ]
    
    # Filter out keys that don't exist to avoid errors
    existing_keys = []
    for key in redis_keys:
        if await redis.exists(key):
            existing_keys.append(key)
    
    if existing_keys:
        await redis.delete(*existing_keys)
        logger.info(f"Cleared Redis data for user {user_id}: {len(existing_keys)} keys")
    else:
        logger.info(f"No Redis data found for user {user_id}")
    
    # 2. Clear PostgreSQL data - check if table exists first
    try:
        async with pool.connection() as conn:
            # First check if the table exists
            table_check = await conn.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'langgraph_checkpoints'
                )
            """)
            table_exists = await table_check.fetchone()
            
            if table_exists and table_exists[0]:
                # Execute the delete query
                try:
                    result = await conn.execute(
                        "DELETE FROM langgraph_checkpoints WHERE thread_id = %s",
                        (user_id,)
                    )
                    
                    # Get the number of rows deleted
                    if hasattr(result, 'rowcount'):
                        rows_deleted = result.rowcount
                        if rows_deleted > 0:
                            logger.info(f"Cleared {rows_deleted} checkpoints for user {user_id}")
                        else:
                            logger.info(f"No checkpoints found for user {user_id}")
                    else:
                        logger.info(f"Checkpoint deletion completed for user {user_id}")
                except Exception as e:
                    # Log the specific error for the DELETE operation
                    logger.error(f"Error executing DELETE query: {str(e)}")
            else:
                logger.info("Table 'langgraph_checkpoints' does not exist, skipping checkpoint deletion")
    except Exception as e:
        logger.error(f"Error checking for checkpoint table: {str(e)}")
    
    # 3. Clear vector memories if store is provided
    if store:
        try:
            # First, try to understand the structure of memories by examining them
            try:
                # Try to list all namespaces to understand the structure
                if hasattr(store, 'alist_namespaces'):
                    try:
                        namespaces = await store.alist_namespaces(limit=100)
                        logger.info(f"Available namespaces: {namespaces}")
                        
                        # Try to search in each namespace for user data
                        for namespace in namespaces:
                            try:
                                # Try to search in this namespace
                                if hasattr(store, 'asearch'):
                                    memories = await store.asearch(namespace, limit=100)
                                    
                                    # Check if any memories contain the user_id
                                    for memory in memories:
                                        memory_str = str(memory.value) if hasattr(memory, 'value') else str(memory)
                                        if user_id in memory_str:
                                            logger.info(f"Found user memory in namespace {namespace}: {memory}")
                                            
                                            # Try to delete this memory
                                            if hasattr(memory, 'key'):
                                                try:
                                                    await store.adelete(namespace, memory.key)
                                                    logger.info(f"Deleted memory with namespace={namespace}, key={memory.key}")
                                                except Exception as e:
                                                    logger.error(f"Error deleting memory from namespace {namespace}: {str(e)}")
                            except Exception as e:
                                logger.error(f"Error searching in namespace {namespace}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error listing namespaces: {str(e)}")
                
                # Check if the store has asearch method to find all memories
                if hasattr(store, 'asearch'):
                    # Try to search for all memories to understand their structure
                    try:
                        # Search with empty query to get all memories
                        all_memories = await store.asearch(("memories",), limit=100)
                        if all_memories:
                            # Log sample memory structure
                            sample = all_memories[0] if all_memories else None
                            logger.info(f"Memory structure sample: {sample}")
                            
                            # Look for user-related memories
                            user_memories = []
                            for memory in all_memories:
                                # Check if memory contains user_id in any field
                                memory_str = str(memory.value) if hasattr(memory, 'value') else str(memory)
                                if user_id in memory_str:
                                    user_memories.append(memory)
                                    
                                    # Log the structure of this memory to understand how user_id is stored
                                    logger.info(f"Found user memory: {memory}")
                                    
                                    # Try to extract namespace and key
                                    if hasattr(memory, 'namespace') and hasattr(memory, 'key'):
                                        try:
                                            # Try to delete this specific memory
                                            await store.adelete(memory.namespace, memory.key)
                                            logger.info(f"Deleted memory with namespace={memory.namespace}, key={memory.key}")
                                        except Exception as e:
                                            logger.error(f"Error deleting specific memory: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error searching memories: {str(e)}")
            except Exception as e:
                logger.error(f"Error examining memory structure: {str(e)}")
                
            # Check if the store has the necessary methods
            if hasattr(store, 'get_by_metadata'):
                # Try to get memories by metadata
                try:
                    # Try different metadata fields that might contain the user ID
                    user_memories = []
                    
                    # Try thread_id
                    thread_memories = await store.get_by_metadata("thread_id", user_id)
                    if thread_memories:
                        user_memories.extend(thread_memories)
                    
                    # Try user_id
                    user_id_memories = await store.get_by_metadata("user_id", user_id)
                    if user_id_memories:
                        user_memories.extend(user_id_memories)
                    
                    logger.info(f"Found {len(user_memories)} memories for user {user_id}")
                    
                    # Delete found memories
                    for memory in user_memories:
                        if hasattr(memory, 'id'):
                            try:
                                await store.adelete(memory.id)
                                logger.info(f"Deleted memory with ID: {memory.id}")
                            except Exception as mem_e:
                                logger.error(f"Error deleting memory {memory.id}: {str(mem_e)}")
                    
                except Exception as e:
                    logger.error(f"Error retrieving memories by metadata: {str(e)}")
            
            # If the store has a delete_by_metadata method, try that
            elif hasattr(store, 'delete_by_metadata'):
                try:
                    # Try different metadata fields
                    deleted_count = 0
                    
                    # Try thread_id
                    result = await store.delete_by_metadata("thread_id", user_id)
                    if result and hasattr(result, 'deleted_count'):
                        deleted_count += result.deleted_count
                    
                    # Try user_id
                    result = await store.delete_by_metadata("user_id", user_id)
                    if result and hasattr(result, 'deleted_count'):
                        deleted_count += result.deleted_count
                    
                    logger.info(f"Deleted {deleted_count} memories using delete_by_metadata")
                    
                except Exception as e:
                    logger.error(f"Error deleting memories by metadata: {str(e)}")
            
            # If the store has aremove_by_metadata method, try that
            elif hasattr(store, 'aremove_by_metadata'):
                try:
                    # Try different metadata fields
                    
                    # Try thread_id
                    try:
                        await store.aremove_by_metadata("thread_id", user_id)
                        logger.info(f"Removed memories with thread_id={user_id}")
                    except Exception as e1:
                        logger.error(f"Error removing by thread_id: {str(e1)}")
                    
                    # Try user_id
                    try:
                        await store.aremove_by_metadata("user_id", user_id)
                        logger.info(f"Removed memories with user_id={user_id}")
                    except Exception as e2:
                        logger.error(f"Error removing by user_id: {str(e2)}")
                    
                except Exception as e:
                    logger.error(f"Error using aremove_by_metadata: {str(e)}")
            
            # If the store has adelete_keys method, try that
            elif hasattr(store, 'adelete_keys'):
                try:
                    # Try with different namespaces
                    
                    # Try with "memories" namespace
                    try:
                        # Try to get all keys first
                        if hasattr(store, 'aget_keys'):
                            keys = await store.aget_keys(("memories",))
                            # Filter keys that might be related to this user
                            user_keys = [k for k in keys if str(user_id) in str(k)]
                            if user_keys:
                                await store.adelete_keys(("memories",), user_keys)
                                logger.info(f"Deleted {len(user_keys)} keys from memories namespace")
                    except Exception as e1:
                        logger.error(f"Error deleting keys from memories namespace: {str(e1)}")
                    
                    # Try with user-specific namespace
                    try:
                        await store.adelete_keys(("users", user_id), ["memory"])
                        logger.info(f"Deleted keys from users/{user_id} namespace")
                    except Exception as e2:
                        logger.error(f"Error deleting keys from users namespace: {str(e2)}")
                    
                    # Try with threads namespace
                    try:
                        await store.adelete_keys(("threads", user_id), ["memory"])
                        logger.info(f"Deleted keys from threads/{user_id} namespace")
                    except Exception as e3:
                        logger.error(f"Error deleting keys from threads namespace: {str(e3)}")
                    
                except Exception as e:
                    logger.error(f"Error using adelete_keys method: {str(e)}")
            
            # If the store has an adelete method, try that
            elif hasattr(store, 'adelete'):
                try:
                    # According to the LangGraph documentation, adelete takes (namespace, key) parameters
                    # Try different namespace approaches
                    
                    # Try with "memories" namespace
                    try:
                        await store.adelete(("memories",), user_id)
                        logger.info(f"Deleted memory with key={user_id} from memories namespace")
                    except Exception as e1:
                        logger.error(f"Error deleting from memories namespace: {str(e1)}")
                    
                    # Try with user-specific namespace
                    try:
                        await store.adelete(("users", user_id), "memory")
                        logger.info(f"Deleted memory from users/{user_id} namespace")
                    except Exception as e2:
                        logger.error(f"Error deleting from users namespace: {str(e2)}")
                    
                    # Try with threads namespace
                    try:
                        await store.adelete(("threads", user_id), "memory")
                        logger.info(f"Deleted memory from threads/{user_id} namespace")
                    except Exception as e3:
                        logger.error(f"Error deleting from threads namespace: {str(e3)}")
                    
                    # Try with user_id as namespace
                    try:
                        await store.adelete((user_id,), "memory")
                        logger.info(f"Deleted memory from {user_id} namespace")
                    except Exception as e4:
                        logger.error(f"Error deleting from user_id namespace: {str(e4)}")
                        
                except Exception as e:
                    logger.error(f"Error using adelete method: {str(e)}")
            
            # Last resort: If the store has a clear method for a specific collection
            elif hasattr(store, 'aclear'):
                logger.warning(f"Could not find specific deletion methods, checking if we can clear user collection")
                try:
                    # Check if there's a user-specific collection
                    user_collection = f"user:{user_id}"
                    if hasattr(store, 'has_collection') and await store.has_collection(user_collection):
                        await store.aclear(user_collection)
                        logger.info(f"Cleared collection {user_collection}")
                except Exception as e:
                    logger.error(f"Error clearing user collection: {str(e)}")
            
            # Try batch operations if available
            if hasattr(store, 'abatch'):
                try:
                    # Try to use batch operations to delete memories
                    logger.info("Attempting batch deletion of memories")
                    
                    # Create a batch of delete operations
                    delete_ops = []
                    
                    # Try different namespaces
                    namespaces_to_try = [
                        ("memories",),
                        ("users", user_id),
                        ("threads", user_id),
                        (user_id,),
                        ("langchain",),
                        ("langchain", "memory"),
                        ("langchain", "memory", user_id)
                    ]
                    
                    for namespace in namespaces_to_try:
                        # Try to delete with this namespace
                        delete_ops.append(("adelete", namespace, user_id))
                    
                    # Execute the batch operations
                    if delete_ops:
                        await store.abatch(delete_ops)
                        logger.info(f"Executed batch deletion with {len(delete_ops)} operations")
                except Exception as e:
                    logger.error(f"Error using batch operations: {str(e)}")
            
            else:
                logger.warning(f"Could not find appropriate methods to delete memories for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error clearing vector memories for user {user_id}: {str(e)}")
    
    logger.info(f"Successfully cleared data for user {user_id}")
