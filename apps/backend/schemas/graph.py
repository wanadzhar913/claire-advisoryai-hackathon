"""This file contains the graph schema for the application."""

from typing import (
    Annotated,
    Any,
    Optional,
)

from langgraph.graph.message import add_messages
from pydantic import (
    BaseModel,
    Field,
)


class GraphState(BaseModel):
    """State definition for the LangGraph Agent/Workflow."""

    messages: Annotated[list, add_messages] = Field(
        default_factory=list, description="The messages in the conversation"
    )
    long_term_memory: str = Field(default="", description="The long term memory of the conversation")
    user_id: Optional[int] = Field(
        default=None,
        description="Authenticated application user id (used to scope DB-backed tools).",
    )
    file_id: Optional[str] = Field(
        default=None,
        description="Optional file ID to scope transaction tools (demo mode).",
    )
    last_sankey: Any = Field(
        default=None,
        description="Last Sankey diagram payload produced by tools (stored for UI usage; not meant to be shown verbatim).",
    )