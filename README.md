# 🤖 LangGraph Telegram Bot

A production-ready Telegram bot with long-term memory capabilities using LangGraph, PostgreSQL vector storage, and Redis rate limiting.

[![Docker](https://img.shields.io/badge/Docker-Containerized-blue)](https://www.docker.com)
[![LangGraph](https://img.shields.io/badge/Powered_by-LangGraph-FF6F00)](https://langchain.com/langgraph)
[![PostgreSQL](https://img.shields.io/badge/Storage-PostgreSQL-336791)](https://www.postgresql.org)

## Features

- 🧠 **Long-term Memory** with pgvector similarity search
- ⚡ **Async Architecture** for high concurrency
- 🔄 **State Management** with LangGraph checkpoints
- 🚦 **Smart Rate Limiting** for LLM calls, not message input
- 📦 **Message Aggregation** with atomic Redis operations
- 🐳 **Dockerized** for easy deployment
- 📈 **Production-Ready** scaling capabilities
- 🔧 **Frontend Explorer** to view collected memories and user profiles




## Quick Start

```bash
# Clone repository
git clone https://github.com/francescofano/langgraph-telegram-bot.git
cd langgraph-telegram-bot

# Setup environment
cp .env.example .env
# Edit .env with your credentials

# Start services
docker-compose up --build
```

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Telegram Bot Token (@BotFather)
- OpenAI API Key
- PostgreSQL 15+ with pgvector
- Redis 7+

## Installation

1. **Set up environment variables**
```bash
# Database configuration
PG_CONNECTION_STRING=postgresql://user:pass@host:port/db
REDIS_URL=redis://redis:6379/0

# Telegram configuration
TELEGRAM_TOKEN=your_telegram_bot_token
DEBOUNCE_TIME=5.0
LLM_CALLS_PER_MINUTE=5

# Agent configuration
LLM_MODEL=gpt-4o-mini
EMBED_MODEL=openai:text-embedding-3-small
VECTOR_DIMS=1536

# API Keys
OPENAI_API_KEY=your_openai_key
```

2. **Start services**
```bash
docker-compose -f docker-compose.yml up --build
```


## Configuration

| Environment Variable       | Description                          | Default                     |
|----------------------------|--------------------------------------|-----------------------------|
| `TELEGRAM_TOKEN`           | Telegram bot token from @BotFather   | Required                    |
| `OPENAI_API_KEY`           | OpenAI API key                       | Required                    |
| `PG_CONNECTION_STRING`     | PostgreSQL connection string         | `postgres://localhost:5432`|
| `REDIS_URL`                | Redis connection URL                 | `redis://localhost:6379/0` |
| `LLM_MODEL`                | OpenAI model version                 | `gpt-4o-mini`              |
| `EMBED_MODEL`              | Embedding model                      | `text-embedding-3-small`    |
| `VECTOR_DIMS`              | Vector dimensions                    | `1536`                      |
| `DEBOUNCE_TIME`            | Message aggregation wait time (sec)  | `5.0`                       |
| `LLM_CALLS_PER_MINUTE`     | Rate limit for LLM API calls         | `5`                         |
| `LOG_LEVEL`                | Logging verbosity                    | `INFO`                      |

## Development

```bash
# Start development environment with hot-reload
docker-compose -f docker-compose.dev.yml up --build

```

## Extending the Bot

### Adding New Agent Capabilities

To extend the agent's capabilities, modify the `agent/agent_factory.py` file:

```python
# Example: Adding a new tool to the agent
from langmem import create_manage_memory_tool
from some_package import create_custom_tool

class AgentFactory:
    @staticmethod
    async def create_agent(...):
        return create_react_agent(
            f"openai:{llm_model}",
            prompt=AgentFactory.create_prompt,
            tools=[
                create_manage_memory_tool(namespace=("memories",)),
                create_custom_tool()  # Add your custom tool here
            ],
            checkpointer=checkpointer,
            store=store,
        )
```

### Implementing Advanced Graph

The `create_advanced_graph` method in `agent/agent_factory.py` provides a placeholder for implementing a more complex LangGraph:

```python
@staticmethod
async def create_advanced_graph(...):
    graph = StateGraph(Any)
    
    
    graph.add_node("classify_intent", classify_user_intent)
    graph.add_node("answer_question", answer_general_question)
    
    # Define edges
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "question": "answer_question",
            "search": "search_knowledge"
        }
    )
    
    # Set the entry point
    graph.set_entry_point("classify_intent")
    
    return graph
```

## Deployment

1. **Production Scaling**
```bash
# Scale bot instances
docker-compose up --scale bot=3 -d

# Add healthchecks
curl http://localhost:8000/health
```


# LangGraph Telegram Bot Frontend

A Next.js dashboard for viewing user memories from the LangGraph Telegram Bot.

## Features

- View all users with stored memories
- Browse memories for each user
- Real-time updates using SWR
- Responsive design with Tailwind CSS
- Dark mode support
- Prisma ORM for database access



 
The application will be available at http://localhost:3000.

## PgAdmin Access

Access at http://localhost:5050 and connect using:
- Host: postgres (Docker service name)
- Port: 5432
- Username: langbotuser
- Password: yourpassword



## License

MIT License - see [LICENSE](LICENSE) for details

---

Made with ❤️ by Francesco # langgraph-telegram-bot
