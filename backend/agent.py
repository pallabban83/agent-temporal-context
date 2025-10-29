"""
Temporal Context RAG Agent using Google's Agent Development Kit (ADK)

This agent manages Vector Search operations with temporal context awareness.
"""

from google.adk.agents import Agent
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

from vector_search_manager import VectorSearchManager
from temporal_embeddings import TemporalEmbeddingHandler
from config import settings
from logging_config import get_logger

logger = get_logger(__name__)


class TemporalRAGAgent:
    """Agent for managing temporal context Vector Search operations using Google's ADK."""

    def __init__(self):
        """Initialize the agent."""
        logger.info(
            "Initializing TemporalRAGAgent",
            extra={'embedding_requests_per_minute': settings.embedding_requests_per_minute}
        )

        # Store tool execution results for chat responses
        self.last_tool_results = []

        self.embedding_handler = TemporalEmbeddingHandler(
            project_id=settings.google_cloud_project,
            location=settings.google_cloud_location,
            model_name=settings.embedding_model_name,
            requests_per_minute=settings.embedding_requests_per_minute
        )
        self.vector_search_manager = VectorSearchManager(
            project_id=settings.google_cloud_project,
            location=settings.google_cloud_location,
            index_name=settings.vertex_ai_corpus_name,
            embedding_handler=self.embedding_handler,
            gcs_bucket_name=settings.gcs_bucket_name,
            vector_search_index=settings.vector_search_index,
            vector_search_endpoint=settings.vector_search_index_endpoint
        )

        # Initialize session service and runner for ADK
        from google.adk.sessions import InMemorySessionService
        from google.adk.runners import Runner

        self.session_service = InMemorySessionService()

        # Create ADK agent with tool functions
        # Configure Vertex AI credentials via environment variables
        import os
        os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = 'true'
        os.environ['GOOGLE_CLOUD_PROJECT'] = settings.google_cloud_project
        os.environ['GOOGLE_CLOUD_LOCATION'] = settings.google_cloud_location

        from google.adk.models import Gemini

        # Create a Gemini model instance
        llm_model = Gemini(model="gemini-2.5-flash")

        self.agent = Agent(
            name="temporal_vector_search_agent",
            model=llm_model,
            description="A helpful Vector Search assistant that searches documents for data/facts questions, and responds directly to greetings and capability inquiries",
            instruction="""You are a Vector Search assistant that helps users query and manage documents.

⚠️ TOOL USAGE RULES:

When to call query_index (MANDATORY):
- Any question asking for data, facts, numbers, or information (e.g., "What was revenue?", "Show me earnings")
- Questions about specific topics, dates, people, or events
- Questions with words like "what", "how much", "when", "show me", "find", "tell me about"
- Comparison questions (e.g., "compare X and Y")
→ For these questions, ALWAYS call query_index FIRST, then answer using the retrieved documents

When NOT to call query_index:
- Greetings (e.g., "hello", "hi", "how are you")
- Questions about YOUR capabilities (e.g., "what can you do?", "how do you work?")
- Questions about the system itself (e.g., "what is this?", "how does this work?")
→ For these, answer directly without calling query_index

Your capabilities:
- Import documents with temporal metadata into Vector Search
- Query documents with semantic search and temporal filtering
- Extract temporal information from text

The query_index tool automatically retrieves the optimal number of results and applies:
- Vector similarity search to find relevant documents
- Temporal filtering and sorting when dates are mentioned or "latest" is requested
- You just need to provide the query text - the system handles the rest

IMPORTANT Response Guidelines:
- ALWAYS call query_index FIRST for every user question
- Provide detailed, verbose, and comprehensive answers based on the retrieved documents
- Include relevant context, numbers, dates, and explanations from the retrieved documents
- Break down complex information into clear, well-structured responses
- Do NOT add source citations or document references (e.g., "Source: document.pdf") in your response text
- The UI automatically displays sources in a separate section below your answer""",
            tools=[
                self.import_documents,
                self.query_index,
                self.get_index_info,
                self.extract_temporal_context
            ]
        )

        # Initialize runner
        self.runner = Runner(
            agent=self.agent,
            app_name="temporal_rag_app",
            session_service=self.session_service
        )

    # Tool functions (ADK will automatically convert these to tool declarations)

    async def import_documents(self, documents: List[Dict[str, Any]], bucket_name: Optional[str] = None) -> Dict[str, Any]:
        """Imports documents into Vector Search with temporal context extraction.

        Documents are embedded with date awareness and stored in Vector Search.

        Args:
            documents: List of documents to import, each with 'content' and optional 'metadata' fields
            bucket_name: Optional GCS bucket name for document storage

        Returns:
            Import result
        """
        try:
            result = await self.vector_search_manager.import_documents(
                documents=documents,
                bucket_name=bucket_name
            )
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Error importing documents: {str(e)}")
            return {"success": False, "error": str(e)}

    async def query_index(self, query: str, temporal_filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """MANDATORY: Search the Vector Search index - CALL THIS FOR EVERY USER QUESTION.

        CRITICAL: You MUST call this tool FIRST before answering ANY user question.
        Do not try to answer from your own knowledge - always search the index first.

        This performs semantic search with temporal awareness to retrieve relevant documents.
        The system automatically handles result ranking, temporal filtering, and sorting.

        Args:
            query: The user's question or query text
            temporal_filter: Optional temporal filtering criteria (e.g., {'document_date': '2024-01-01'})

        Returns:
            Query results with matching documents that you should use to formulate your answer
        """
        try:
            # Always use configured default top_k (LLM should not control this)
            top_k = settings.default_top_k
            logger.info(f"Querying index: '{query}' (top_k={top_k})")
            result = await self.vector_search_manager.query(
                query_text=query,
                top_k=top_k,
                temporal_filter=temporal_filter
            )

            # Log query results
            if result and 'results' in result:
                logger.info(f"Query returned {len(result['results'])} results")
                for i, res in enumerate(result['results'][:3]):  # Log first 3 results
                    title = res.get('title', 'Unknown')
                    score = res.get('score', 0)
                    logger.info(f"  Result {i+1}: {title} (score: {score:.3f})")
            else:
                logger.info("Query returned no results")

            # Store result for chat response
            tool_result = {"success": True, "result": result}
            self.last_tool_results.append({
                "tool": "query_index",
                "input": {"query": query, "temporal_filter": temporal_filter},
                "result": tool_result
            })

            return tool_result
        except Exception as e:
            logger.error(f"Error querying index: {str(e)}")
            error_result = {"success": False, "error": str(e)}
            self.last_tool_results.append({
                "tool": "query_index",
                "input": {"query": query, "temporal_filter": temporal_filter},
                "result": error_result
            })
            return error_result

    async def get_index_info(self) -> Dict[str, Any]:
        """Retrieves information about the current Vector Search index.

        Returns index details including status, endpoint details, and document count.

        Returns:
            Index information
        """
        try:
            result = await self.vector_search_manager.get_index_info()
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Error getting index info: {str(e)}")
            return {"success": False, "error": str(e)}

    def extract_temporal_context(self, text: str) -> Dict[str, Any]:
        """Extracts temporal information (dates, years, time references) from text.

        Args:
            text: Text to analyze for temporal entities

        Returns:
            Extracted temporal entities
        """
        try:
            temporal_info = self.embedding_handler.extract_temporal_info(text)
            return {"success": True, "result": temporal_info}
        except Exception as e:
            logger.error(f"Error extracting temporal context: {str(e)}")
            return {"success": False, "error": str(e)}

    async def chat(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None,
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """Process a user message with tool execution capabilities.

        Args:
            user_message: User's message
            conversation_history: Previous conversation messages (not used, maintained by session)
            session_id: Optional session ID to maintain conversation context
            user_id: User identifier (default: "default_user")

        Returns:
            Agent response with tool results and session_id
        """
        try:
            logger.info(f"Processing message: {user_message}")

            # Clear previous tool results
            self.last_tool_results = []

            from google.genai import types

            # Use provided session_id or create a new one
            if not session_id:
                import uuid
                session_id = str(uuid.uuid4())
                logger.info(f"Creating new session: {session_id}")

                # Create session in the session service
                await self.session_service.create_session(
                    app_name="temporal_rag_app",
                    user_id=user_id,
                    session_id=session_id
                )
                logger.info(f"Session created successfully")
            else:
                logger.info(f"Using existing session: {session_id}")

                # Check if session exists, if not create it
                try:
                    await self.session_service.get_session(
                        app_name="temporal_rag_app",
                        user_id=user_id,
                        session_id=session_id
                    )
                except:
                    logger.info(f"Session not found, creating: {session_id}")
                    await self.session_service.create_session(
                        app_name="temporal_rag_app",
                        user_id=user_id,
                        session_id=session_id
                    )

            # Create the message content
            user_content = types.Content(
                role='user',
                parts=[types.Part(text=user_message)]
            )

            # Run the agent and collect events
            final_response = ""

            # Use async version directly with persistent runner and session
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_content
            ):
                # Get final response from events
                if event.is_final_response() and event.content:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            final_response += part.text

            # Use tool results that were stored during tool execution
            tool_results = self.last_tool_results
            logger.info(f"Collected {len(tool_results)} tool results")

            return {
                "response": final_response or "Operation completed",
                "tool_results": tool_results,
                "session_id": session_id,  # Return session_id so frontend can reuse it
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "response": f"Error: {str(e)}",
                "tool_results": [],
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }

    async def import_docs(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convenience method to import documents.

        Args:
            documents: List of documents

        Returns:
            Import result
        """
        result = await self.import_documents(documents=documents)
        return result

    async def query(self, query_text: str, temporal_filter: Optional[Dict] = None) -> Dict[str, Any]:
        """Convenience method to query the index.

        Args:
            query_text: Query text
            temporal_filter: Temporal filtering criteria

        Returns:
            Query results
        """
        result = await self.query_index(
            query=query_text,
            temporal_filter=temporal_filter
        )
        return result
