"""Chatbot API endpoints for handling chat interactions.

This module provides endpoints for chat interactions, including regular chat,
streaming chat, message history management, and chat history clearing.
"""

import json
import asyncio
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


async def _get_demo_file_id(user_id: int) -> str | None:
    try:
        uploads = await asyncio.to_thread(
            database_service.get_user_uploads,
            user_id=user_id,
            limit=50,
            offset=0,
            order_by="created_at",
            order_desc=True,
        )
        demo = next((u for u in uploads if u.file_name == "demo_data.json"), None)
        return demo.file_id if demo else None
    except Exception:
        return None


# from fastapi.security import (
#     HTTPAuthorizationCredentials,
#     HTTPBearer,
# )
# security = HTTPBearer()

# TODO: Implement JWT verification properly. For now, support per-user sessions via headers
# forwarded by the Next.js adapter route.
async def get_current_session(request: Request) -> Session:
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
    clerk_user_id = request.headers.get("x-clerk-user-id")
    clerk_email = request.headers.get("x-clerk-user-email")

    # Prefer stable per-user thread IDs when available (keeps LangGraph memory/checkpoints per user).
    if clerk_user_id:
        user = await database_service.get_user_by_clerk_id(clerk_user_id)
        if user is None:
            # Create a placeholder user record if backend hasn't seen this Clerk user yet.
            # Email is required + unique; fall back to a deterministic placeholder.
            email = clerk_email or f"{clerk_user_id}@clerk.local"
            user = await database_service.create_user_from_clerk(clerk_id=clerk_user_id, email=email)

        if await database_service.get_session(session_id=clerk_user_id) is None:
            await database_service.create_session(session_id=clerk_user_id, user_id=user.id)

        return Session(id=clerk_user_id, user_id=user.id)

    # Fallback behavior for local/dev without Clerk headers.
    if await database_service.get_session(session_id="1") is None:
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

        demo_mode = request.headers.get("x-demo-mode") == "true"
        demo_file_id = await _get_demo_file_id(session.user_id) if demo_mode else None

        result = await agent.get_response(
            chat_request.messages,
            session.id,
            user_id=session.user_id,
            file_id=demo_file_id,
        )

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
                demo_mode = request.headers.get("x-demo-mode") == "true"
                demo_file_id = await _get_demo_file_id(session.user_id) if demo_mode else None

                async for chunk in agent.get_stream_response(
                    chat_request.messages,
                    session.id,
                    user_id=session.user_id,
                    file_id=demo_file_id,
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