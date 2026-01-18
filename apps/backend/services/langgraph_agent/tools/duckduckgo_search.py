"""DuckDuckGo search tool for LangGraph.

This module provides a DuckDuckGo search tool that can be used with LangGraph
to perform web searches. It returns up to 10 search results and handles errors
gracefully.

Note: DNS errors may occur in Docker environments. The tool is configured to
handle errors gracefully and return user-friendly messages.
"""
from langchain_community.tools import DuckDuckGoSearchResults

# Create the tool with error handling enabled
# handle_tool_error=True ensures errors are caught and returned as tool messages
# rather than crashing the agent
duckduckgo_search_tool = DuckDuckGoSearchResults(
    num_results=10,
    handle_tool_error=True,
)