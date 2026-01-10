"""Tests for conversation summary service."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageRole
from app.models.user import User
from app.services.summary_service import (
    SummaryService,
    SummaryAnalysis,
    ConceptUnderstood,
    ConceptStruggled,
)


# Test Pydantic schemas
class TestSummaryAnalysisSchema:
    """Tests for SummaryAnalysis Pydantic model."""

    def test_valid_analysis(self):
        """Test creating a valid SummaryAnalysis."""
        data = {
            "summary": "Student explored neural networks with good engagement.",
            "topics_covered": ["neural networks", "backpropagation"],
            "concepts_understood": [
                {"concept": "activation functions", "confidence": 0.9, "evidence": "explained correctly"}
            ],
            "concepts_struggled": [
                {"concept": "gradient descent", "severity": "medium", "evidence": "confused"}
            ],
            "questions_asked": 5,
            "engagement_level": "high",
            "engagement_score": 0.85,
            "recommended_next_steps": ["practice more examples"],
            "prerequisite_gaps": ["calculus basics"],
        }

        analysis = SummaryAnalysis.model_validate(data)

        assert analysis.summary == data["summary"]
        assert analysis.topics_covered == data["topics_covered"]
        assert len(analysis.concepts_understood) == 1
        assert analysis.engagement_score == 0.85
        assert analysis.engagement_level == "high"

    def test_default_values(self):
        """Test SummaryAnalysis with minimal data uses defaults."""
        analysis = SummaryAnalysis()

        assert analysis.summary == "Conversation completed."
        assert analysis.topics_covered == []
        assert analysis.concepts_understood == []
        assert analysis.engagement_score == 0.5
        assert analysis.engagement_level == "medium"

    def test_engagement_score_bounds(self):
        """Test engagement score is clamped to valid range."""
        # Valid scores should work
        analysis = SummaryAnalysis(engagement_score=0.0)
        assert analysis.engagement_score == 0.0

        analysis = SummaryAnalysis(engagement_score=1.0)
        assert analysis.engagement_score == 1.0

    def test_severity_validation(self):
        """Test severity field validation."""
        struggled = ConceptStruggled(
            concept="test",
            severity="INVALID",
            evidence="test"
        )
        # Should normalize to "medium"
        assert struggled.severity == "medium"

        struggled = ConceptStruggled(
            concept="test",
            severity="HIGH",
            evidence="test"
        )
        assert struggled.severity == "high"

    def test_get_concepts_understood_strings(self):
        """Test extracting concept names as strings."""
        analysis = SummaryAnalysis(
            concepts_understood=[
                ConceptUnderstood(concept="concept1", confidence=0.8, evidence="..."),
                "concept2",  # String format
                {"concept": "concept3", "confidence": 0.9},  # Dict format
            ]
        )

        strings = analysis.get_concepts_understood_strings()
        assert "concept1" in strings
        assert "concept2" in strings
        assert "concept3" in strings

    def test_get_concepts_struggled_strings(self):
        """Test extracting struggled concept names as strings."""
        analysis = SummaryAnalysis(
            concepts_struggled=[
                ConceptStruggled(concept="concept1", severity="high", evidence="..."),
                "concept2",
            ]
        )

        strings = analysis.get_concepts_struggled_strings()
        assert "concept1" in strings
        assert "concept2" in strings


class TestSummaryServiceJSONParsing:
    """Tests for JSON parsing robustness."""

    def test_extract_json_from_plain_json(self):
        """Test extracting plain JSON."""
        service = MagicMock(spec=SummaryService)
        service._extract_json = SummaryService._extract_json

        text = '{"summary": "Test", "topics_covered": []}'
        result = service._extract_json(service, text)

        assert result is not None
        assert "summary" in result

    def test_extract_json_from_markdown_code_block(self):
        """Test extracting JSON from markdown code block."""
        service = MagicMock(spec=SummaryService)
        service._extract_json = SummaryService._extract_json

        text = '''Here's the analysis:

```json
{
    "summary": "Test summary",
    "topics_covered": ["topic1"]
}
```

That's the result.'''

        result = service._extract_json(service, text)

        assert result is not None
        data = json.loads(result)
        assert data["summary"] == "Test summary"

    def test_extract_json_from_markdown_without_language(self):
        """Test extracting JSON from markdown code block without json specifier."""
        service = MagicMock(spec=SummaryService)
        service._extract_json = SummaryService._extract_json

        text = '''```
{"summary": "Test", "topics_covered": []}
```'''

        result = service._extract_json(service, text)

        assert result is not None
        data = json.loads(result)
        assert data["summary"] == "Test"

    def test_extract_json_with_surrounding_text(self):
        """Test extracting JSON with text before and after."""
        service = MagicMock(spec=SummaryService)
        service._extract_json = SummaryService._extract_json

        text = '''Based on my analysis, here is the summary:

{"summary": "The student learned about neural networks.", "topics_covered": ["neural networks", "deep learning"], "engagement_score": 0.8}

I hope this helps!'''

        result = service._extract_json(service, text)

        assert result is not None
        data = json.loads(result)
        assert data["summary"] == "The student learned about neural networks."

    def test_extract_json_nested_objects(self):
        """Test extracting JSON with nested objects."""
        service = MagicMock(spec=SummaryService)
        service._extract_json = SummaryService._extract_json

        text = '''{"summary": "Test", "concepts_understood": [{"concept": "test", "confidence": 0.8}]}'''

        result = service._extract_json(service, text)

        assert result is not None
        data = json.loads(result)
        assert len(data["concepts_understood"]) == 1

    def test_extract_json_returns_none_for_invalid(self):
        """Test that invalid text returns None."""
        service = MagicMock(spec=SummaryService)
        service._extract_json = SummaryService._extract_json

        text = "This has no JSON at all."

        result = service._extract_json(service, text)
        assert result is None


class TestSummaryServiceFallback:
    """Tests for fallback analysis when Claude fails."""

    def test_fallback_counts_questions(self):
        """Test that fallback analysis counts question marks."""
        service = MagicMock(spec=SummaryService)
        service._create_fallback_analysis = SummaryService._create_fallback_analysis

        messages = [
            {"role": "user", "content": "What is this? How does it work?"},
            {"role": "assistant", "content": "Let me explain..."},
            {"role": "user", "content": "Can you clarify?"},
        ]

        analysis = service._create_fallback_analysis(service, messages)

        # Should count 3 question marks
        assert analysis.questions_asked_by_student == 3

    def test_fallback_estimates_engagement(self):
        """Test that fallback analysis estimates engagement from message patterns."""
        service = MagicMock(spec=SummaryService)
        service._create_fallback_analysis = SummaryService._create_fallback_analysis

        # High engagement: Many messages, longer content
        messages = [
            {"role": "user", "content": "I've been thinking about this concept and I believe it works by " + "x" * 100},
            {"role": "assistant", "content": "Good thinking!"},
            {"role": "user", "content": "But what about this edge case? I'm curious because " + "y" * 100},
            {"role": "assistant", "content": "Great question!"},
            {"role": "user", "content": "That makes sense now. Let me verify my understanding: " + "z" * 100},
        ]

        analysis = service._create_fallback_analysis(service, messages)

        # Should detect high engagement
        assert analysis.engagement_level == "high"
        assert analysis.engagement_score >= 0.7

    def test_fallback_low_engagement(self):
        """Test fallback detects low engagement."""
        service = MagicMock(spec=SummaryService)
        service._create_fallback_analysis = SummaryService._create_fallback_analysis

        # Low engagement: Few short messages
        messages = [
            {"role": "user", "content": "ok"},
            {"role": "assistant", "content": "Would you like to know more?"},
        ]

        analysis = service._create_fallback_analysis(service, messages)

        assert analysis.engagement_level == "low"
        assert analysis.engagement_score < 0.5


# Integration-style tests (require API keys, skipped by default)
@pytest.fixture
async def sample_user(db_session):
    """Create a sample user."""
    user = User(
        id=uuid4(),
        supabase_id="test-supabase-id",
        email="test@example.com",
        name="Test User",
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def sample_book(db_session):
    """Create a sample book."""
    book = Book(
        id=uuid4(),
        title="Test Book on Machine Learning",
        author="Test Author",
        description="A test book",
        created_at=datetime.utcnow(),
    )
    db_session.add(book)
    await db_session.commit()
    return book


@pytest.fixture
async def sample_chapter(db_session, sample_book):
    """Create a sample chapter."""
    chapter = Chapter(
        id=uuid4(),
        book_id=sample_book.id,
        title="Introduction to Neural Networks",
        chapter_number=1,
        summary="This chapter introduces neural networks",
        key_concepts=["neural networks", "backpropagation", "activation functions"],
        prerequisites=[],
        created_at=datetime.utcnow(),
    )
    db_session.add(chapter)
    await db_session.commit()
    return chapter


@pytest.fixture
async def sample_conversation(db_session, sample_user, sample_chapter):
    """Create a sample conversation."""
    conversation = Conversation(
        id=uuid4(),
        user_id=sample_user.id,
        chapter_id=sample_chapter.id,
        started_at=datetime.utcnow(),
        status=ConversationStatus.ACTIVE,
    )
    db_session.add(conversation)
    await db_session.commit()
    return conversation


@pytest.fixture
def sample_messages(sample_conversation):
    """Create sample messages."""
    return [
        Message(
            id=uuid4(),
            conversation_id=sample_conversation.id,
            role=MessageRole.ASSISTANT,
            content="Welcome! What do you know about neural networks?",
            created_at=datetime.utcnow(),
        ),
        Message(
            id=uuid4(),
            conversation_id=sample_conversation.id,
            role=MessageRole.USER,
            content="I think they're like the brain? They have neurons that connect?",
            created_at=datetime.utcnow(),
        ),
        Message(
            id=uuid4(),
            conversation_id=sample_conversation.id,
            role=MessageRole.ASSISTANT,
            content="Good intuition! How do you think these 'neurons' pass information to each other?",
            created_at=datetime.utcnow(),
        ),
        Message(
            id=uuid4(),
            conversation_id=sample_conversation.id,
            role=MessageRole.USER,
            content="Maybe through some kind of signal? Like electricity?",
            created_at=datetime.utcnow(),
        ),
    ]


@pytest.mark.asyncio
async def test_generate_summary_integration(
    db_session, sample_conversation, sample_messages
):
    """Test full summary generation (requires API key)."""
    pytest.skip("Requires Anthropic API key - skipping")

    # Add messages to session
    for msg in sample_messages:
        db_session.add(msg)
    await db_session.commit()

    service = SummaryService(db_session)
    summary = await service.generate_summary(
        conversation=sample_conversation,
        messages=sample_messages,
    )

    assert summary is not None
    assert summary.conversation_id == sample_conversation.id
    assert len(summary.summary) > 0
    assert isinstance(summary.topics_covered, list)


@pytest.mark.asyncio
async def test_generate_summary_empty_messages(db_session, sample_conversation):
    """Test that empty messages raises ValueError."""
    service = SummaryService(db_session)

    with pytest.raises(ValueError, match="no messages"):
        await service.generate_summary(
            conversation=sample_conversation,
            messages=[],
        )


@pytest.mark.asyncio
async def test_summary_service_with_mocked_claude(
    db_session, sample_conversation, sample_messages
):
    """Test summary generation with mocked Claude response."""
    # Add messages
    for msg in sample_messages:
        db_session.add(msg)
    await db_session.commit()

    # Mock Claude response
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text=json.dumps({
                "summary": "Student explored neural network basics with good engagement.",
                "topics_covered": ["neural networks", "neurons"],
                "concepts_understood": [
                    {"concept": "neuron structure", "confidence": 0.8, "evidence": "correct analogy"}
                ],
                "concepts_struggled": [],
                "questions_asked": 2,
                "engagement_level": "high",
                "engagement_score": 0.8,
                "recommended_next_steps": ["learn about activation functions"],
                "prerequisite_gaps": [],
            })
        )
    ]

    with patch.object(SummaryService, "_analyze_conversation") as mock_analyze:
        # Create a proper SummaryAnalysis object
        mock_analyze.return_value = SummaryAnalysis(
            summary="Student explored neural network basics with good engagement.",
            topics_covered=["neural networks", "neurons"],
            concepts_understood=[
                ConceptUnderstood(concept="neuron structure", confidence=0.8, evidence="correct analogy")
            ],
            concepts_struggled=[],
            questions_asked=2,
            engagement_level="high",
            engagement_score=0.8,
            recommended_next_steps=["learn about activation functions"],
            prerequisite_gaps=[],
        )

        service = SummaryService(db_session)
        summary = await service.generate_summary(
            conversation=sample_conversation,
            messages=sample_messages,
        )

        assert summary is not None
        assert "neural network" in summary.summary.lower()
        assert summary.engagement_score == 0.8
        assert "neural networks" in summary.topics_covered
