"""
WebSocket search streaming handler.

Handles real-time search result streaming over WebSocket connections.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Any

from services.ai.search.agent import HybridSearchAgent
from services.ai.search.types import SearchFilters

from .types import (
    WebSocketMessage,
    WebSocketMessageType,
    SearchStreamRequest,
    SearchStreamResult,
    AuthenticationError,
    StreamingError
)
from .manager import WebSocketManager

logger = logging.getLogger(__name__)


class SearchStreamHandler:
    """
    Handles WebSocket search streaming operations.

    Provides real-time search result streaming with batching and error handling.
    """

    def __init__(self, manager: WebSocketManager):
        """Initialize search stream handler."""
        self.manager = manager
        self.search_agent = HybridSearchAgent()

        # Active search streams by connection ID
        self._active_searches: Dict[str, asyncio.Task] = {}

        logger.info("SearchStreamHandler initialized")

    async def handle_search_start(self, connection_id: str, message: WebSocketMessage) -> None:
        """Handle search streaming request."""
        try:
            # Validate authentication
            conn_info = self.manager.get_connection_info(connection_id)
            if not conn_info or not conn_info.user_id:
                raise AuthenticationError("Authentication required for search")

            # Parse search request
            search_request = SearchStreamRequest(**message.data)

            # Cancel any existing search for this connection
            if connection_id in self._active_searches:
                self._active_searches[connection_id].cancel()

            # Start streaming search
            search_task = asyncio.create_task(
                self._stream_search_results(
                    connection_id,
                    search_request,
                    message.correlation_id
                )
            )

            self._active_searches[connection_id] = search_task

            logger.info(
                f"Started search stream for {connection_id}: {search_request.query}")

        except Exception as e:
            logger.error(f"Search start error for {connection_id}: {e}")
            await self.manager._send_to_connection(
                connection_id,
                WebSocketMessage(
                    type=WebSocketMessageType.SEARCH_ERROR,
                    data={
                        "error": str(e),
                        "error_code": getattr(e, 'error_code', 'SEARCH_ERROR')
                    },
                    correlation_id=message.correlation_id
                )
            )

    async def _stream_search_results(
        self,
        connection_id: str,
        request: SearchStreamRequest,
        correlation_id: Optional[str] = None
    ) -> None:
        """Stream search results to a WebSocket connection."""
        try:
            # Initialize search agent if needed
            if not self.search_agent._initialized:
                await self.search_agent.initialize()

            # Build search filters
            filters = None
            if request.filters:
                filters = SearchFilters(**request.filters)

            # Perform search
            search_response = await self.search_agent.search(
                query_text=request.query,
                filters=filters,
                limit=request.limit,
                include_suggestions=request.include_suggestions
            )

            # Stream results in batches
            batch_size = 10
            total_results = len(search_response.results)
            total_batches = (total_results + batch_size - 1) // batch_size

            for batch_index in range(total_batches):
                start_idx = batch_index * batch_size
                end_idx = min(start_idx + batch_size, total_results)
                batch_results = search_response.results[start_idx:end_idx]

                # Send batch of results
                for result in batch_results:
                    stream_result = SearchStreamResult(
                        result=result,
                        batch_index=batch_index,
                        total_batches=total_batches,
                        is_final=False
                    )

                    await self.manager._send_to_connection(
                        connection_id,
                        WebSocketMessage(
                            type=WebSocketMessageType.SEARCH_RESULT,
                            data=stream_result.model_dump(),
                            correlation_id=correlation_id
                        )
                    )

                # Small delay between batches to prevent overwhelming
                if batch_index < total_batches - 1:
                    await asyncio.sleep(0.1)

            # Send completion message
            await self.manager._send_to_connection(
                connection_id,
                WebSocketMessage(
                    type=WebSocketMessageType.SEARCH_COMPLETE,
                    data={
                        "total_results": total_results,
                        "total_batches": total_batches,
                        "processing_time_ms": search_response.stats.processing_time_ms,
                        "suggestions": [s.model_dump() for s in search_response.suggestions] if search_response.suggestions else [],
                        "stats": search_response.stats.model_dump()
                    },
                    correlation_id=correlation_id
                )
            )

            logger.info(
                f"Search stream completed for {connection_id}: {total_results} results")

        except asyncio.CancelledError:
            logger.info(f"Search stream cancelled for {connection_id}")
        except Exception as e:
            logger.error(f"Search streaming error for {connection_id}: {e}")

            await self.manager._send_to_connection(
                connection_id,
                WebSocketMessage(
                    type=WebSocketMessageType.SEARCH_ERROR,
                    data={
                        "error": str(e),
                        "error_code": "STREAMING_ERROR"
                    },
                    correlation_id=correlation_id
                )
            )
        finally:
            # Clean up active search
            if connection_id in self._active_searches:
                del self._active_searches[connection_id]

    async def cleanup_connection(self, connection_id: str) -> None:
        """Clean up resources for a disconnected connection."""
        # Cancel any active searches
        if connection_id in self._active_searches:
            self._active_searches[connection_id].cancel()
            del self._active_searches[connection_id]

    def get_active_searches(self) -> Dict[str, str]:
        """Get information about active searches."""
        return {
            connection_id: "running" if not task.done() else "completed"
            for connection_id, task in self._active_searches.items()
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on search handler."""
        try:
            return {
                "status": "healthy",
                "active_searches": len(self._active_searches),
                "search_agent_initialized": self.search_agent._initialized,
                "last_check": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
