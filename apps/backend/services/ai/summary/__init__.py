"""
Summary Generation Package

AI-powered conversation summarization with:
- Brief, detailed, and insight summaries
- Thread and contact summaries
- Prompt template management
- Integration with Ollama
"""

from services.ai.summary.agent import (
    SummaryAgent,
    SummaryType,
    get_summary_agent,
)

__all__ = [
    "SummaryAgent",
    "SummaryType",
    "get_summary_agent",
]
