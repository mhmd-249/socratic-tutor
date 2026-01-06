"""API endpoints for conversations and chat."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Schemas
class StartConversationRequest(BaseModel):
    """Request to start a new conversation."""

    chapter_id: str = Field(..., description="Chapter UUID")


class StartConversationResponse(BaseModel):
    """Response when starting a conversation."""

    conversation_id: str
    chapter: dict
    message: str


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""

    message: str = Field(..., min_length=1, max_length=5000)


class SendMessageResponse(BaseModel):
    """Response from assistant."""

    message: str
    sources: list[dict]


class ConversationMessage(BaseModel):
    """A single message in conversation history."""

    id: str
    role: str
    content: str
    created_at: str


class ConversationHistoryResponse(BaseModel):
    """Full conversation history."""

    conversation_id: str
    messages: list[ConversationMessage]


class EndConversationResponse(BaseModel):
    """Response when ending a conversation."""

    conversation_id: str
    status: str
    message: str


# Endpoints
@router.post(
    "/conversations/start",
    response_model=StartConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new conversation",
    description="Start a new Socratic tutoring conversation for a specific chapter",
)
async def start_conversation(
    request: StartConversationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a new conversation for a chapter.

    Args:
        request: Request with chapter_id
        current_user: Authenticated user
        db: Database session

    Returns:
        Conversation data with initial greeting

    Raises:
        HTTPException: If chapter not found or error occurs
    """
    try:
        chat_service = ChatService(db)

        result = await chat_service.start_conversation(
            user_id=current_user.id,
            chapter_id=UUID(request.chapter_id),
        )

        return StartConversationResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(e), "code": "CHAPTER_NOT_FOUND"},
        )
    except Exception as e:
        logger.error(f"Error starting conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to start conversation", "code": "INTERNAL_ERROR"},
        )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
    summary="Send a message",
    description="Send a message in an active conversation and get AI response",
)
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message and get AI response.

    Args:
        conversation_id: Conversation UUID
        request: Request with message content
        current_user: Authenticated user
        db: Database session

    Returns:
        Assistant's response with sources

    Raises:
        HTTPException: If conversation not found, inactive, or error occurs
    """
    try:
        chat_service = ChatService(db)

        result = await chat_service.send_message(
            conversation_id=UUID(conversation_id),
            user_message=request.message,
        )

        return SendMessageResponse(**result)

    except ValueError as e:
        error_message = str(e).lower()
        if "not found" in error_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": str(e), "code": "CONVERSATION_NOT_FOUND"},
            )
        elif "not active" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": str(e), "code": "CONVERSATION_NOT_ACTIVE"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": str(e), "code": "INVALID_REQUEST"},
            )
    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to send message", "code": "INTERNAL_ERROR"},
        )


@router.get(
    "/conversations/{conversation_id}/history",
    response_model=ConversationHistoryResponse,
    summary="Get conversation history",
    description="Retrieve full message history for a conversation",
)
async def get_conversation_history(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get full conversation history.

    Args:
        conversation_id: Conversation UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        List of all messages in the conversation

    Raises:
        HTTPException: If conversation not found or error occurs
    """
    try:
        chat_service = ChatService(db)

        messages = await chat_service.get_conversation_history(
            conversation_id=UUID(conversation_id)
        )

        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            messages=[ConversationMessage(**msg) for msg in messages],
        )

    except Exception as e:
        logger.error(f"Error getting conversation history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to get conversation history", "code": "INTERNAL_ERROR"},
        )


@router.post(
    "/conversations/{conversation_id}/end",
    response_model=EndConversationResponse,
    summary="End a conversation",
    description="Mark a conversation as completed",
)
async def end_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    End a conversation.

    Args:
        conversation_id: Conversation UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Confirmation message

    Raises:
        HTTPException: If conversation not found or error occurs
    """
    try:
        chat_service = ChatService(db)

        result = await chat_service.end_conversation(
            conversation_id=UUID(conversation_id)
        )

        return EndConversationResponse(**result)

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
