"""Integration tests for conversation API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

from app.main import app
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.conversation import Conversation, ConversationStatus
from app.models.conversation_summary import ConversationSummary
from app.models.user import User


@pytest.fixture
async def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(
        id=uuid4(),
        supabase_id="test-supabase-id",
        email="test@example.com",
        name="Test User",
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_book(db_session):
    """Create a sample book for testing."""
    book = Book(
        id=uuid4(),
        title="Test Book on Machine Learning",
        author="Test Author",
        description="A test book about ML",
        created_at=datetime.utcnow(),
    )
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)
    return book


@pytest.fixture
async def sample_chapter(db_session, sample_book):
    """Create a sample chapter for testing."""
    chapter = Chapter(
        id=uuid4(),
        book_id=sample_book.id,
        title="Introduction to Neural Networks",
        chapter_number=1,
        summary="This chapter introduces neural networks",
        key_concepts=["neural networks", "backpropagation"],
        prerequisites=[],
        created_at=datetime.utcnow(),
    )
    db_session.add(chapter)
    await db_session.commit()
    await db_session.refresh(chapter)
    return chapter


@pytest.fixture
def mock_auth_token():
    """Mock authentication token."""
    return "Bearer mock-jwt-token"


@pytest.fixture
def auth_headers(mock_auth_token):
    """Authentication headers."""
    return {"Authorization": mock_auth_token}


# Test POST /conversations - Create conversation
@pytest.mark.asyncio
async def test_create_conversation_endpoint(sample_user, sample_chapter, auth_headers):
    """Test creating a conversation via API endpoint."""
    pytest.skip("Requires full API integration setup - skipping for now")

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("app.core.security.get_current_user", return_value=sample_user):
            response = await client.post(
                "/api/v1/conversations",
                json={"chapter_id": str(sample_chapter.id)},
                headers=auth_headers,
            )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "id" in data
    assert "initial_message" in data
    assert data["chapter_id"] == str(sample_chapter.id)
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_create_conversation_invalid_chapter(sample_user, auth_headers):
    """Test creating conversation with invalid chapter ID."""
    pytest.skip("Requires full API integration setup - skipping for now")

    invalid_chapter_id = str(uuid4())

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("app.core.security.get_current_user", return_value=sample_user):
            response = await client.post(
                "/api/v1/conversations",
                json={"chapter_id": invalid_chapter_id},
                headers=auth_headers,
            )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_create_conversation_unauthorized():
    """Test creating conversation without authentication."""
    pytest.skip("Requires full API integration setup - skipping for now")

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/conversations",
            json={"chapter_id": str(uuid4())},
        )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# Test POST /conversations/{id}/messages - Send message with streaming
@pytest.mark.asyncio
async def test_send_message_endpoint_streaming(sample_user, sample_chapter, auth_headers, db_session):
    """Test sending message with SSE streaming."""
    pytest.skip("Requires full API integration setup - skipping for now")

    # Create a conversation first
    conversation = Conversation(
        id=uuid4(),
        user_id=sample_user.id,
        chapter_id=sample_chapter.id,
        started_at=datetime.utcnow(),
        status=ConversationStatus.ACTIVE,
    )
    db_session.add(conversation)
    await db_session.commit()

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("app.core.security.get_current_user", return_value=sample_user):
            response = await client.post(
                f"/api/v1/conversations/{conversation.id}/messages",
                json={"message": "What is a neural network?"},
                headers={**auth_headers, "Accept": "text/event-stream"},
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    # Parse SSE events
    content = response.text
    assert "data:" in content


# Test GET /conversations/{id} - Get conversation
@pytest.mark.asyncio
async def test_get_conversation_endpoint(sample_user, sample_chapter, auth_headers, db_session):
    """Test getting conversation with messages."""
    pytest.skip("Requires full API integration setup - skipping for now")

    # Create a conversation
    conversation = Conversation(
        id=uuid4(),
        user_id=sample_user.id,
        chapter_id=sample_chapter.id,
        started_at=datetime.utcnow(),
        status=ConversationStatus.ACTIVE,
    )
    db_session.add(conversation)
    await db_session.commit()

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("app.core.security.get_current_user", return_value=sample_user):
            response = await client.get(
                f"/api/v1/conversations/{conversation.id}",
                headers=auth_headers,
            )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "conversation" in data
    assert "messages" in data
    assert data["conversation"]["id"] == str(conversation.id)


# Test GET /conversations - List conversations
@pytest.mark.asyncio
async def test_list_conversations_endpoint(sample_user, auth_headers):
    """Test listing user's conversations."""
    pytest.skip("Requires full API integration setup - skipping for now")

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("app.core.security.get_current_user", return_value=sample_user):
            response = await client.get(
                "/api/v1/conversations",
                headers=auth_headers,
            )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "conversations" in data
    assert "total" in data
    assert isinstance(data["conversations"], list)


# Test POST /conversations/{id}/end - End conversation
@pytest.mark.asyncio
async def test_end_conversation_endpoint(sample_user, sample_chapter, auth_headers, db_session):
    """Test ending conversation and getting summary."""
    pytest.skip("Requires full API integration setup - skipping for now")

    # Create a conversation
    conversation = Conversation(
        id=uuid4(),
        user_id=sample_user.id,
        chapter_id=sample_chapter.id,
        started_at=datetime.utcnow(),
        status=ConversationStatus.ACTIVE,
    )
    db_session.add(conversation)
    await db_session.commit()

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("app.core.security.get_current_user", return_value=sample_user):
            response = await client.post(
                f"/api/v1/conversations/{conversation.id}/end",
                headers=auth_headers,
            )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "id" in data
    assert "conversation_id" in data
    assert "summary" in data
    assert "topics_covered" in data
    assert "concepts_understood" in data
    assert "engagement_score" in data


# Test error cases
@pytest.mark.asyncio
async def test_send_message_to_nonexistent_conversation(sample_user, auth_headers):
    """Test sending message to non-existent conversation."""
    pytest.skip("Requires full API integration setup - skipping for now")

    invalid_conversation_id = str(uuid4())

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("app.core.security.get_current_user", return_value=sample_user):
            response = await client.post(
                f"/api/v1/conversations/{invalid_conversation_id}/messages",
                json={"message": "Hello"},
                headers={**auth_headers, "Accept": "text/event-stream"},
            )

    # Should return error in SSE format
    content = response.text
    assert "error" in content.lower() or "not found" in content.lower()


@pytest.mark.asyncio
async def test_request_validation():
    """Test request validation."""
    pytest.skip("Requires full API integration setup - skipping for now")

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Missing chapter_id
        response = await client.post(
            "/api/v1/conversations",
            json={},
        )

    assert response.status_code in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
    ]


@pytest.mark.asyncio
async def test_message_validation(sample_user, auth_headers):
    """Test message content validation."""
    pytest.skip("Requires full API integration setup - skipping for now")

    conversation_id = str(uuid4())

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("app.core.security.get_current_user", return_value=sample_user):
            # Empty message
            response = await client.post(
                f"/api/v1/conversations/{conversation_id}/messages",
                json={"message": ""},
                headers=auth_headers,
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
