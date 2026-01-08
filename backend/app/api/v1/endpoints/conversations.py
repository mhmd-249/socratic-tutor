"""API endpoints for conversations and chat with SSE streaming support."""

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Schemas
class CreateConversationRequest(BaseModel):
    """Request to start a new conversation."""

    chapter_id: str = Field(..., description="Chapter UUID")


class CreateConversationResponse(BaseModel):
    """Response when creating a conversation."""

    id: str
    user_id: str
    chapter_id: str
    started_at: str
    status: str
    initial_message: str


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""

    message: str = Field(..., min_length=1, max_length=5000, description="User's message content")


class ConversationMessage(BaseModel):
    """A single message in conversation history."""

    id: str
    role: str
    content: str
    created_at: str


class GetConversationResponse(BaseModel):
    """Full conversation with messages."""

    conversation: dict[str, Any]
    messages: list[ConversationMessage]


class EndConversationResponse(BaseModel):
    """Response when ending a conversation."""

    id: str
    conversation_id: str
    summary: str
    topics_covered: list[str]
    concepts_understood: list[str]
    concepts_struggled: list[str]
    questions_asked: int
    engagement_score: float
    created_at: str


class ConversationListItem(BaseModel):
    """Summary of a conversation for list view."""

    id: str
    chapter_id: str
    started_at: str
    ended_at: str | None
    status: str


class ListConversationsResponse(BaseModel):
    """List of user's conversations."""

    conversations: list[ConversationListItem]
    total: int


# Endpoints
@router.post(
    "/conversations",
    response_model=CreateConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation",
    description="Start a new Socratic tutoring conversation for a specific chapter",
)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create a new conversation for a chapter.

    Creates a conversation record and generates an initial greeting from the AI tutor.

    Args:
        request: Request with chapter_id
        current_user: Authenticated user
        db: Database session

    Returns:
        Conversation data with initial greeting message

    Raises:
        HTTPException: If chapter not found or error occurs
    """
    try:
        chat_service = ChatService(db)

        # Create conversation and get initial greeting
        conversation = await chat_service.create_conversation(
            user_id=current_user.id,
            chapter_id=UUID(request.chapter_id),
        )

        # Get the initial greeting message
        conversation_data = await chat_service.get_conversation_with_messages(
            conversation.id
        )

        # Extract the initial greeting (first message should be assistant greeting)
        initial_message = ""
        if conversation_data["messages"]:
            initial_message = conversation_data["messages"][0]["content"]

        return {
            "id": str(conversation.id),
            "user_id": str(conversation.user_id),
            "chapter_id": str(conversation.chapter_id),
            "started_at": conversation.started_at.isoformat(),
            "status": conversation.status.value,
            "initial_message": initial_message,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(e), "code": "CHAPTER_NOT_FOUND"},
        )
    except Exception as e:
        logger.error(f"Error creating conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to create conversation", "code": "INTERNAL_ERROR"},
        )


@router.post(
    "/conversations/{conversation_id}/messages",
    summary="Send a message with streaming response",
    description="Send a message in an active conversation and receive AI response via Server-Sent Events (SSE)",
    responses={
        200: {
            "description": "Streaming response",
            "content": {"text/event-stream": {"example": "data: Hello\n\ndata: World\n\n"}},
        }
    },
)
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Send a message and stream AI response via Server-Sent Events.

    This endpoint uses SSE (Server-Sent Events) to stream the AI's response in real-time.
    Each chunk of text is sent as a separate event.

    Args:
        conversation_id: Conversation UUID
        request: Request with message content
        current_user: Authenticated user
        db: Database session

    Returns:
        StreamingResponse with text/event-stream content type

    Raises:
        HTTPException: If conversation not found, inactive, or error occurs
    """

    async def event_stream():
        """Generate SSE events from the chat service stream."""
        try:
            chat_service = ChatService(db)

            # Stream response from chat service
            async for chunk in chat_service.send_message(
                conversation_id=UUID(conversation_id),
                user_message=request.message,
            ):
                # Format as SSE event
                # SSE format: "data: <content>\n\n"
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            # Send completion event
            yield f"data: {json.dumps({'done': True})}\n\n"

        except ValueError as e:
            error_message = str(e).lower()
            if "not found" in error_message:
                error_data = {
                    "error": str(e),
                    "code": "CONVERSATION_NOT_FOUND",
                }
            elif "not active" in error_message or "completed" in error_message:
                error_data = {
                    "error": str(e),
                    "code": "CONVERSATION_NOT_ACTIVE",
                }
            else:
                error_data = {
                    "error": str(e),
                    "code": "INVALID_REQUEST",
                }
            yield f"data: {json.dumps(error_data)}\n\n"

        except Exception as e:
            logger.error(f"Error streaming message: {e}", exc_info=True)
            error_data = {
                "error": "Failed to send message",
                "code": "INTERNAL_ERROR",
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=GetConversationResponse,
    summary="Get conversation with messages",
    description="Retrieve full conversation history with all messages",
)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get full conversation with message history.

    Args:
        conversation_id: Conversation UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Conversation data with list of all messages

    Raises:
        HTTPException: If conversation not found or error occurs
    """
    try:
        chat_service = ChatService(db)

        conversation_data = await chat_service.get_conversation_with_messages(
            conversation_id=UUID(conversation_id)
        )

        return {
            "conversation": conversation_data["conversation"],
            "messages": [
                ConversationMessage(**msg) for msg in conversation_data["messages"]
            ],
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(e), "code": "CONVERSATION_NOT_FOUND"},
        )
    except Exception as e:
        logger.error(f"Error getting conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to get conversation", "code": "INTERNAL_ERROR"},
        )


@router.get(
    "/conversations",
    response_model=ListConversationsResponse,
    summary="List user's conversations",
    description="Get paginated list of conversations for the current user",
)
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List conversations for the current user.

    Args:
        limit: Maximum number of conversations to return (default: 20)
        offset: Offset for pagination (default: 0)
        current_user: Authenticated user
        db: Database session

    Returns:
        List of conversation summaries with pagination info

    Raises:
        HTTPException: If error occurs
    """
    try:
        chat_service = ChatService(db)

        conversations = await chat_service.list_user_conversations(
            user_id=current_user.id,
            limit=limit,
            offset=offset,
        )

        return {
            "conversations": [
                ConversationListItem(**conv) for conv in conversations
            ],
            "total": len(conversations),
        }

    except Exception as e:
        logger.error(f"Error listing conversations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to list conversations", "code": "INTERNAL_ERROR"},
        )


@router.post(
    "/conversations/{conversation_id}/end",
    response_model=EndConversationResponse,
    summary="End a conversation",
    description="Mark a conversation as completed and generate summary",
)
async def end_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    End a conversation and generate summary.

    This triggers:
    1. Conversation status update to COMPLETED
    2. AI-generated summary of the learning session
    3. (Future) Learning profile update based on summary

    Args:
        conversation_id: Conversation UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Conversation summary with topics covered and student performance

    Raises:
        HTTPException: If conversation not found or error occurs
    """
    try:
        chat_service = ChatService(db)

        summary = await chat_service.end_conversation(
            conversation_id=UUID(conversation_id)
        )

        return {
            "id": str(summary.id),
            "conversation_id": str(summary.conversation_id),
            "summary": summary.summary,
            "topics_covered": summary.topics_covered,
            "concepts_understood": summary.concepts_understood,
            "concepts_struggled": summary.concepts_struggled,
            "questions_asked": summary.questions_asked,
            "engagement_score": summary.engagement_score,
            "created_at": summary.created_at.isoformat(),
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(e), "code": "CONVERSATION_NOT_FOUND"},
        )
    except Exception as e:
        logger.error(f"Error ending conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to end conversation", "code": "INTERNAL_ERROR"},
        )
