"""
Agent manager for caching and managing LangGraph agents per user.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from psycopg_pool import AsyncConnectionPool

from agent.agent_factory import AgentFactory

logger = logging.getLogger(__name__)

class AgentManager:
    """
    Manages LangGraph agents for multiple users with caching and cleanup.
    
    This class:
    - Caches agent instances per user ID
    - Provides automatic cleanup of inactive sessions
    - Ensures thread-safe access to agent instances
    """
    
    def __init__(
        self, 
        agent_factory: AgentFactory,
        pg_connection: str,
        pool: AsyncConnectionPool,
        llm_model: str,
        vector_dims: int,
        embed_model: str,
        max_idle_time: int = 1800,  # 30 minutes in seconds
        cleanup_interval: int = 300  # 5 minutes in seconds
    ):
        """
        Initialize the agent manager.
        
        Args:
            agent_factory: Factory for creating agents
            pg_connection: PostgreSQL connection string
            pool: Connection pool for database operations
            llm_model: LLM model identifier
            vector_dims: Dimensions of the vector embeddings
            embed_model: Name of the embedding model
            max_idle_time: Maximum time in seconds an agent can be idle before cleanup
            cleanup_interval: Interval in seconds for running the cleanup task
        """
        self.agent_factory = agent_factory
        self.pg_connection = pg_connection
        self.pool = pool
        self.llm_model = llm_model
        self.vector_dims = vector_dims
        self.embed_model = embed_model
        self.max_idle_time = max_idle_time
        self.cleanup_interval = cleanup_interval
        
        # Agent cache: user_id -> (agent, last_used_timestamp)
        self._agents: Dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"Agent manager initialized with max_idle_time={max_idle_time}s, cleanup_interval={cleanup_interval}s")
    
    async def get_agent(self, user_id: str) -> Any:
        """
        Get or create an agent for the specified user.
        
        Args:
            user_id: User identifier
            
        Returns:
            The agent instance for the user
        """
        async with self._lock:
            current_time = time.time()
            
            # Check if we have a cached agent for this user
            if user_id in self._agents:
                agent, _ = self._agents[user_id]
                # Update last used timestamp
                self._agents[user_id] = (agent, current_time)
                logger.debug(f"Using cached agent for user {user_id}")
                return agent
            
            # Create a new agent for this user
            logger.info(f"Creating new agent for user {user_id}")
            agent = await self.agent_factory.create_agent(
                pg_connection=self.pg_connection,
                pool=self.pool,
                llm_model=self.llm_model,
                vector_dims=self.vector_dims,
                embed_model=self.embed_model,
                user_id=user_id
            )
            
            # Cache the agent
            self._agents[user_id] = (agent, current_time)
            return agent
    
    async def remove_agent(self, user_id: str) -> None:
        """
        Explicitly remove an agent from the cache.
        
        Args:
            user_id: User identifier
        """
        async with self._lock:
            if user_id in self._agents:
                logger.info(f"Explicitly removing agent for user {user_id}")
                del self._agents[user_id]
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up inactive agents"""
        try:
            while True:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_inactive_agents()
        except asyncio.CancelledError:
            logger.info("Agent cleanup task cancelled")
        except Exception as e:
            logger.error(f"Error in agent cleanup task: {str(e)}")
    
    async def _cleanup_inactive_agents(self) -> None:
        """Clean up agents that have been inactive for too long"""
        async with self._lock:
            current_time = time.time()
            users_to_remove = []
            
            for user_id, (_, last_used) in self._agents.items():
                if current_time - last_used > self.max_idle_time:
                    users_to_remove.append(user_id)
            
            for user_id in users_to_remove:
                logger.info(f"Cleaning up inactive agent for user {user_id}")
                del self._agents[user_id]
            
            if users_to_remove:
                logger.info(f"Cleaned up {len(users_to_remove)} inactive agents")
    
    async def shutdown(self) -> None:
        """Shutdown the agent manager and clean up resources"""
        if hasattr(self, '_cleanup_task') and self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Agent manager shut down")
