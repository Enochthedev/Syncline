"""
Factory functions for summary generation agent.
"""

from typing import Optional
from services.ai.base import AIProvider
from .agent import SummaryGenerationAgent

# Global summary generation agent instance
_summary_agent = None


async def get_summary_generation_agent() -> SummaryGenerationAgent:
    """Get the global summary generation agent instance."""
    global _summary_agent
    if _summary_agent is None:
        _summary_agent = SummaryGenerationAgent()
    return _summary_agent


def create_summary_generation_agent(
    provider: Optional[AIProvider] = None,
    model: Optional[str] = None,
    **kwargs
) -> SummaryGenerationAgent:
    """Create a new summary generation agent instance."""
    return SummaryGenerationAgent(
        provider=provider,
        model=model,
        **kwargs
    )
