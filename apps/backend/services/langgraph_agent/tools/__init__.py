"""LangGraph tools for enhanced language model capabilities.

This package contains custom tools that can be used with LangGraph to extend
the capabilities of language models. Currently includes tools for web search
and financial transaction queries.
"""

from langchain_core.tools.base import BaseTool

from .duckduckgo_search import duckduckgo_search_tool
from .query_subscriptions import query_subscriptions_tool
from .query_sankey import query_sankey_tool

tools: list[BaseTool] = [
    duckduckgo_search_tool,
    query_subscriptions_tool,
    query_sankey_tool,
]