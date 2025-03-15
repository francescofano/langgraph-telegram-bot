"""
Factory for creating and configuring LangGraph agents.
"""

import logging
from typing import Any, Dict
from psycopg_pool import AsyncConnectionPool
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langmem import create_manage_memory_tool
from langgraph.prebuilt import create_react_agent
from langgraph.utils.config import get_store

from db.postgres_utils import create_memory_store

from agent.prompts import MEMORY_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class AgentFactory:
    """Factory for creating and configuring LangGraph agents"""
    
    @staticmethod
    async def create_agent(
        pg_connection: str,
        pool: AsyncConnectionPool,
        llm_model: str,
        vector_dims: int,
        embed_model: str,
        user_id: str
    ) -> Any:
        """Initialize LangGraph agent with memory and checkpoints
        
        Args:
            pg_connection: PostgreSQL connection string
            pool: Connection pool for database operations
            llm_model: LLM model identifier
            vector_dims: Dimensions of the vector embeddings
            embed_model: Name of the embedding model
            user_id: User identifier for memory namespace (required)
            
        Returns:
            The created agent
        """
        if not user_id:
            raise ValueError("user_id is required for agent creation")
            
        checkpointer = AsyncPostgresSaver(pool)
        
        # Create the memory store with the connection pool
        store = await create_memory_store(pg_connection, pool, vector_dims, embed_model)
        
        # Use user_id as namespace (no fallback to "memories")
        namespace = (str(user_id),)
        
        # Create a closure that captures user_id
        async def user_specific_prompt(state: Dict[str, Any]) -> list:
            """Generate system prompt with memory context using captured user_id
            
            Args:
                state: Current conversation state
                
            Returns:
                List of messages with system prompt and user messages
            """
            nonlocal user_id, store
            
            logger.info(f"Using captured user_id: {user_id}")
            
            # Use the captured user_id directly - no need to extract from state
            namespace = (str(user_id),)
            
            logger.info(f"Searching memories with namespace={namespace}, user_id={user_id}")
            
            try:
                # Search for memories using the async search method
                memories = await store.asearch(
                    namespace,
                    query=state["messages"][-1].content,
                    limit=10  # Number of memories to retrieve
                )
                
                logger.info(f"Found {len(memories) if memories else 0} memories for namespace={namespace}")
                
                # Format the memories for display with better error handling
                if memories:
                    memory_items = []
                    for item in memories:
                        try:
                            if hasattr(item, 'value') and isinstance(item.value, dict):
                                content = item.value.get('content', 'No content available')
                                memory_items.append(f"- {content}")
                            else:
                                logger.warning(f"Unexpected memory item format: {type(item)}")
                        except Exception as e:
                            logger.error(f"Error processing memory item: {str(e)}")
                    
                    memory_content = "\n".join(memory_items)
                else:
                    memory_content = ""
                    
                logger.info(f"Memory content length: {len(memory_content)}")
            except Exception as e:
                logger.error(f"Error retrieving memories: {str(e)}")
                memory_content = ""
            
            return [
                {"role": "system", "content": MEMORY_SYSTEM_PROMPT.format(memory_content=memory_content)},
                *state["messages"]
            ]
        
        return create_react_agent(
            f"openai:{llm_model}",
            prompt=user_specific_prompt,  # Use the closure instead of the class method
            tools=[create_manage_memory_tool(namespace=namespace)],
            checkpointer=checkpointer,
            store=store
        )
    
    @staticmethod
    async def create_advanced_graph(
        pg_connection: str,
        pool: AsyncConnectionPool,
        vector_dims: int,
        embed_model: str
    ) -> StateGraph:
        """
        Create a more complex LangGraph for advanced conversational capabilities.
        
        This is where you can improve the graph and make it more complex:
        - Add multiple nodes for different processing steps
        - Implement conditional routing based on message content
        - Add specialized handlers for different types of queries
        - Implement multi-step reasoning
        - Add external API integrations
        
        Args:
            pg_connection: PostgreSQL connection string
            pool: Connection pool for database operations
            vector_dims: Dimensions of the vector embeddings
            embed_model: Name of the embedding model
            
        Returns:
            StateGraph: The created graph
        """
        # This is a placeholder for your improved graph implementation
        graph = StateGraph(Any)
        
        # Create the memory store for the graph with the connection pool
        store = await create_memory_store(pg_connection, pool, vector_dims, embed_model)
        
        # Example of how you might expand this:
        # 
        # # Define nodes
        # graph.add_node("classify_intent", classify_user_intent)
        # graph.add_node("answer_question", answer_general_question)
        # graph.add_node("search_knowledge", search_knowledge_base)
        # graph.add_node("generate_response", generate_final_response)
        # 
        # # Define edges
        # graph.add_edge("classify_intent", "answer_question")
        # graph.add_conditional_edges(
        #     "classify_intent",
        #     route_by_intent,
        #     {
        #         "question": "answer_question",
        #         "search": "search_knowledge",
        #         "task": "perform_task"
        #     }
        # )
        # graph.add_edge("search_knowledge", "generate_response")
        # graph.add_edge("answer_question", "generate_response")
        
        # Set the entry point
        # graph.set_entry_point("classify_intent")
        
        # Set the store for the graph
        # graph.set_store(store)
        
        return graph
