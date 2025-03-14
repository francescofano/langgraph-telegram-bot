"""
PostgreSQL database utilities for connection management and vector storage.
"""

import logging
from psycopg_pool import AsyncConnectionPool
from psycopg import AsyncConnection
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres import AsyncPostgresStore

logger = logging.getLogger(__name__)

async def setup_database(pg_connection: str) -> AsyncConnectionPool:
    """Initialize database connection pool and setup schema
    
    Args:
        pg_connection: PostgreSQL connection string
        
    Returns:
        AsyncConnectionPool: Connection pool for database operations
    """
    # Import dict_row cursor factory
    from psycopg.rows import dict_row
    
    # Schema setup connection with dict_row cursor factory
    setup_conn = await AsyncConnection.connect(
        pg_connection, 
        autocommit=True,
        row_factory=dict_row
    )
    checkpointer = AsyncPostgresSaver(setup_conn)
    await checkpointer.setup()
    await setup_conn.close()

    # Main connection pool with dict_row cursor factory
    pool = AsyncConnectionPool(
        conninfo=pg_connection,
        max_size=100,
        timeout=30,
        kwargs={"row_factory": dict_row}  # Configure all connections to use dict_row
    )
    await pool.open()
    return pool

async def create_memory_store(pg_connection: str, pool: AsyncConnectionPool, 
                             vector_dims: int, embed_model: str) -> AsyncPostgresStore:
    """Initialize PostgreSQL store for memory management
    
    Args:
        pg_connection: PostgreSQL connection string
        pool: Connection pool for database operations
        vector_dims: Dimensions of the vector embeddings
        embed_model: Name of the embedding model
        
    Returns:
        AsyncPostgresStore: Store for vector operations
    """
    # Import dict_row cursor factory
    from psycopg.rows import dict_row
    
    # Create a separate connection with autocommit=True and dict_row cursor factory
    setup_conn = await AsyncConnection.connect(
        pg_connection, 
        autocommit=True,
        row_factory=dict_row
    )
    
    try:
        # Create a temporary store for setup
        setup_store = AsyncPostgresStore(
            conn=setup_conn,
            index={
                "dims": vector_dims,
                "embed": embed_model
            }
        )
        
        # Run setup on the autocommit connection
        logger.info("Setting up PostgreSQL store schema with autocommit connection")
        await setup_store.setup()
    finally:
        # Always close the setup connection
        await setup_conn.close()
    
    # Now create the real store with the connection pool
    logger.info("Creating PostgreSQL store with connection pool")
    store = AsyncPostgresStore(
        conn=pool,
        index={
            "dims": vector_dims,
            "embed": embed_model
        }
    )
    
    return store
