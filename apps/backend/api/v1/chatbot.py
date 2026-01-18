"""Chatbot API endpoints for handling chat interactions.

This module provides endpoints for chat interactions, including regular chat,
streaming chat, message history management, and chat history clearing.
"""

import json
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from fastapi.responses import StreamingResponse

from backend.config import settings
from backend.services.langgraph_agent.graph import LangGraphAgent
from backend.core.logging_config import logger
from backend.models.session import Session
from backend.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Message,
    StreamResponse,
)
from backend.services.db.postgres_connector import database_service

router = APIRouter()
agent = LangGraphAgent()


# from fastapi.security import (
#     HTTPAuthorizationCredentials,
#     HTTPBearer,
# )
# security = HTTPBearer()

# TODO: Implement this function (and Auth & JWT in general)
async def get_current_session(
    # credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Session:
    """Get the current session ID from the token.

    Args:
        credentials: The HTTP authorization credentials containing the JWT token.

    Returns:
        Session: The session extracted from the token.

    Raises:
        HTTPException: If the token is invalid or missing.
    """
    # try:
    #     # Sanitize token
    #     token = sanitize_string(credentials.credentials)

    #     session_id = verify_token(token)
    #     if session_id is None:
    #         logger.error("session_id_not_found", token_part=token[:10] + "...")
    #         raise HTTPException(
    #             status_code=401,
    #             detail="Invalid authentication credentials",
    #             headers={"WWW-Authenticate": "Bearer"},
    #         )

    #     # Sanitize session_id before using it
    #     session_id = sanitize_string(session_id)

    #     # Verify session exists in database
    #     session = await db_service.get_session(session_id)
    #     if session is None:
    #         logger.error("session_not_found", session_id=session_id)
    #         raise HTTPException(
    #             status_code=404,
    #             detail="Session not found",
    #             headers={"WWW-Authenticate": "Bearer"},
    #         )

    #     return session
    # except ValueError as ve:
    #     logger.error("token_validation_failed", error=str(ve), exc_info=True)
    #     raise HTTPException(
    #         status_code=422,
    #         detail="Invalid token format",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )
    if database_service.get_session(session_id="1") is None:
        await database_service.create_session(session_id="1", user_id=1)
    return Session(id="1", user_id=1)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    chat_request: ChatRequest,
    session: Session = Depends(get_current_session),
):
    """Process a chat request using LangGraph.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        session: The current session from the auth token.

    Returns:
        ChatResponse: The processed chat response.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        logger.info(
            "chat_request_received",
            session_id=session.id,
            message_count=len(chat_request.messages),
        )

        result = await agent.get_response(chat_request.messages, session.id, user_id=session.user_id)

        logger.info("chat_request_processed", session_id=session.id)

        return ChatResponse(messages=result)
    except Exception as e:
        logger.error("chat_request_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    session: Session = Depends(get_current_session),
):
    """Process a chat request using LangGraph with streaming response.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        session: The current session from the auth token.

    Returns:
        StreamingResponse: A streaming response of the chat completion.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        logger.info(
            "stream_chat_request_received",
            session_id=session.id,
            message_count=len(chat_request.messages),
        )

        async def event_generator():
            """Generate streaming events.

            Yields:
                str: Server-sent events in JSON format.

            Raises:
                Exception: If there's an error during streaming.
            """
            try:
                full_response = ""
                async for chunk in agent.get_stream_response(
                    chat_request.messages, session.id, user_id=session.user_id
                ):
                    full_response += chunk
                    response = StreamResponse(content=chunk, done=False)
                    yield f"data: {json.dumps(response.model_dump())}\n\n"

                # Send final message indicating completion
                final_response = StreamResponse(content="", done=True)
                yield f"data: {json.dumps(final_response.model_dump())}\n\n"

            except Exception as e:
                logger.error(
                    "stream_chat_request_failed",
                    session_id=session.id,
                    error=str(e),
                    exc_info=True,
                )
                error_response = StreamResponse(content=str(e), done=True)
                yield f"data: {json.dumps(error_response.model_dump())}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.error(
            "stream_chat_request_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages", response_model=ChatResponse)
async def get_session_messages(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get all messages for a session.

    Args:
        request: The FastAPI request object for rate limiting.
        session: The current session from the auth token.

    Returns:
        ChatResponse: All messages in the session.

    Raises:
        HTTPException: If there's an error retrieving the messages.
    """
    try:
        messages = await agent.get_chat_history(session.id)
        return ChatResponse(messages=messages)
    except Exception as e:
        logger.error("get_messages_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/messages")
async def clear_chat_history(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Clear all messages for a session.

    Args:
        request: The FastAPI request object for rate limiting.
        session: The current session from the auth token.

    Returns:
        dict: A message indicating the chat history was cleared.
    """
    try:
        await agent.clear_chat_history(session.id)
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        logger.error("clear_chat_history_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))