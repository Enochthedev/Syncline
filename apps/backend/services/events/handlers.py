"""
Event Handler Framework

This module provides the base event handler framework with:
- Abstract base handler class
- Handler registration and routing
- Error handling and retries
- Handler lifecycle management
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from services.events.types import Event, EventType

logger = logging.getLogger(__name__)


class BaseEventHandler(ABC):
    """
    Abstract base class for event handlers.
    
    All event handlers should inherit from this class and implement
    the handle() method to process specific event types.
    """
    
    def __init__(self):
        """Initialize the event handler."""
        self.name = self.__class__.__name__
        self.logger = logging.getLogger(f"handlers.{self.name}")
    
    @abstractmethod
    async def handle(self, event: Event) -> None:
        """
        Handle an event.
        
        This method must be implemented by subclasses to process
        specific event types.
        
        Args:
            event: Event to handle
        
        Raises:
            Exception: If event processing fails
        """
        pass
    
    @abstractmethod
    def can_handle(self, event_type: EventType) -> bool:
        """
        Check if this handler can process the given event type.
        
        Args:
            event_type: Event type to check
        
        Returns:
            True if handler can process this event type
        """
        pass
    
    async def on_error(self, event: Event, error: Exception) -> None:
        """
        Handle errors that occur during event processing.
        
        Override this method to implement custom error handling.
        
        Args:
            event: Event that caused the error
            error: Exception that occurred
        """
        self.logger.error(
            f"Error handling event {event.event_type.value} "
            f"(id={event.event_id}): {error}",
            exc_info=True
        )
    
    async def before_handle(self, event: Event) -> None:
        """
        Hook called before handling an event.
        
        Override this method to implement pre-processing logic.
        
        Args:
            event: Event about to be handled
        """
        pass
    
    async def after_handle(self, event: Event) -> None:
        """
        Hook called after successfully handling an event.
        
        Override this method to implement post-processing logic.
        
        Args:
            event: Event that was handled
        """
        pass
    
    async def process(self, event: Event) -> None:
        """
        Process an event with lifecycle hooks and error handling.
        
        This method wraps the handle() method with before/after hooks
        and error handling.
        
        Args:
            event: Event to process
        """
        try:
            # Pre-processing hook
            await self.before_handle(event)
            
            # Main event handling
            await self.handle(event)
            
            # Post-processing hook
            await self.after_handle(event)
            
            self.logger.debug(
                f"Successfully handled event {event.event_type.value} "
                f"(id={event.event_id})"
            )
        
        except Exception as e:
            await self.on_error(event, e)
            raise


class EventRouter:
    """
    Routes events to appropriate handlers.
    
    The router maintains a registry of handlers and dispatches
    events to handlers that can process them.
    """
    
    def __init__(self):
        """Initialize the event router."""
        self.handlers: list[BaseEventHandler] = []
        self.logger = logging.getLogger("EventRouter")
    
    def register(self, handler: BaseEventHandler) -> None:
        """
        Register an event handler.
        
        Args:
            handler: Handler to register
        """
        if handler not in self.handlers:
            self.handlers.append(handler)
            self.logger.info(f"Registered handler: {handler.name}")
        else:
            self.logger.warning(f"Handler already registered: {handler.name}")
    
    def unregister(self, handler: BaseEventHandler) -> None:
        """
        Unregister an event handler.
        
        Args:
            handler: Handler to unregister
        """
        if handler in self.handlers:
            self.handlers.remove(handler)
            self.logger.info(f"Unregistered handler: {handler.name}")
        else:
            self.logger.warning(f"Handler not found: {handler.name}")
    
    def get_handlers_for_event(self, event_type: EventType) -> list[BaseEventHandler]:
        """
        Get all handlers that can process the given event type.
        
        Args:
            event_type: Event type to find handlers for
        
        Returns:
            List of handlers that can process this event type
        """
        return [h for h in self.handlers if h.can_handle(event_type)]
    
    async def route(self, event: Event) -> None:
        """
        Route an event to all appropriate handlers.
        
        Args:
            event: Event to route
        """
        handlers = self.get_handlers_for_event(event.event_type)
        
        if not handlers:
            self.logger.warning(
                f"No handlers found for event type: {event.event_type.value}"
            )
            return
        
        self.logger.debug(
            f"Routing event {event.event_type.value} to {len(handlers)} handler(s)"
        )
        
        # Process event with all matching handlers
        errors = []
        for handler in handlers:
            try:
                await handler.process(event)
            except Exception as e:
                errors.append((handler.name, e))
        
        # Log any errors that occurred
        if errors:
            error_summary = ", ".join([f"{name}: {err}" for name, err in errors])
            self.logger.error(
                f"Errors occurred while routing event {event.event_type.value}: "
                f"{error_summary}"
            )


class EventDispatcher:
    """
    Dispatches events with routing and error handling.
    
    The dispatcher coordinates event routing and provides
    additional features like event filtering and metrics.
    """
    
    def __init__(self, router: EventRouter | None = None):
        """
        Initialize the event dispatcher.
        
        Args:
            router: Optional event router instance
        """
        self.router = router or EventRouter()
        self.logger = logging.getLogger("EventDispatcher")
        self._event_count = 0
        self._error_count = 0
    
    def register_handler(self, handler: BaseEventHandler) -> None:
        """
        Register an event handler with the router.
        
        Args:
            handler: Handler to register
        """
        self.router.register(handler)
    
    def unregister_handler(self, handler: BaseEventHandler) -> None:
        """
        Unregister an event handler from the router.
        
        Args:
            handler: Handler to unregister
        """
        self.router.unregister(handler)
    
    async def dispatch(self, event: Event) -> None:
        """
        Dispatch an event to appropriate handlers.
        
        Args:
            event: Event to dispatch
        """
        self._event_count += 1
        
        try:
            await self.router.route(event)
        except Exception as e:
            self._error_count += 1
            self.logger.error(
                f"Error dispatching event {event.event_type.value}: {e}",
                exc_info=True
            )
            raise
    
    def get_stats(self) -> dict[str, Any]:
        """
        Get dispatcher statistics.
        
        Returns:
            Dictionary with dispatcher statistics
        """
        return {
            "total_events": self._event_count,
            "total_errors": self._error_count,
            "registered_handlers": len(self.router.handlers),
            "error_rate": (
                self._error_count / self._event_count
                if self._event_count > 0
                else 0.0
            ),
        }
    
    def reset_stats(self) -> None:
        """Reset dispatcher statistics."""
        self._event_count = 0
        self._error_count = 0


# Global dispatcher instance
_dispatcher: EventDispatcher | None = None


def get_dispatcher() -> EventDispatcher:
    """
    Get or create the global event dispatcher.
    
    Returns:
        EventDispatcher instance
    """
    global _dispatcher
    
    if _dispatcher is None:
        _dispatcher = EventDispatcher()
    
    return _dispatcher


# Export public API
__all__ = [
    "BaseEventHandler",
    "EventRouter",
    "EventDispatcher",
    "get_dispatcher",
]
