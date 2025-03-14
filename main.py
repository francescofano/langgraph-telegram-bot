"""
Main entry point for the Telegram bot application.
"""

import asyncio
import logging
from redis.asyncio import Redis

from config.bot_config import BotConfig
from config.agent_config import AgentConfig
from db.postgres_utils import setup_database, create_memory_store
from agent.agent_factory import AgentFactory
from telegram_adapter.telegram_bot import TelegramBot
from core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the application"""
    try:
        # Load configuration
        bot_config = BotConfig()
        agent_config = AgentConfig()
        
        # Validate required configuration
        if not bot_config.telegram_token:
            raise ConfigurationError("Missing Telegram token")
        if not bot_config.pg_connection:
            raise ConfigurationError("Missing PostgreSQL connection string")
        
        # Setup database
        logger.info("Setting up database connection")
        pool = await setup_database(bot_config.pg_connection)
        
        # Create Redis connection
        logger.info(f"Connecting to Redis at {bot_config.redis_url}")
        redis = Redis.from_url(bot_config.redis_url, decode_responses=True)
        # Test connection
        await redis.ping()
        
        # Create memory store
        logger.info("Creating memory store")
        store = await create_memory_store(
            pg_connection=agent_config.pg_connection,
            pool=pool,
            vector_dims=agent_config.vector_dims,
            embed_model=agent_config.embed_model
        )
        
        # Create agent
        logger.info(f"Creating agent with model {agent_config.llm_model}")
        agent_factory = AgentFactory()
        agent = await agent_factory.create_agent(
            pg_connection=agent_config.pg_connection,
            pool=pool,
            llm_model=agent_config.llm_model,
            vector_dims=agent_config.vector_dims,
            embed_model=agent_config.embed_model
        )
        
        # Create and run Telegram bot
        logger.info("Starting Telegram bot")
        telegram_bot = TelegramBot(redis, bot_config, agent, pool=pool, store=store)
        await telegram_bot.run()
    except ConfigurationError as e:
        logger.critical(f"Configuration error: {str(e)}")
        raise
    except Exception as e:
        logger.critical(f"Application failed to start: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.critical(f"Application failed: {str(e)}")
        raise
