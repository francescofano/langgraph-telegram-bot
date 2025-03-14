"""
Agent-specific configuration settings.
"""

import os
from dataclasses import dataclass
from config.base_config import BaseConfig

@dataclass
class AgentConfig(BaseConfig):
    """Agent-specific configuration settings loaded from environment variables"""
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    embed_model: str = os.getenv("EMBED_MODEL", "openai:text-embedding-3-small")
    vector_dims: int = int(os.getenv("VECTOR_DIMS", "1536"))
