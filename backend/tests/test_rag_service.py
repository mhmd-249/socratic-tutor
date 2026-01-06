"""Tests for RAG service with hybrid search."""

import pytest
from uuid import uuid4
from datetime import datetime

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.chunk import Chunk
from app.models.message import Message
from app.services.rag_service import RAGService, RetrievedChunk, RAGContext


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
        key_concepts=["neural networks", "backpropagation", "activation functions"],
        prerequisites=[],
        created_at=datetime.utcnow(),
    )
    db_session.add(chapter)
    await db_session.commit()
    await db_session.refresh(chapter)
    return chapter


@pytest.fixture
async def sample_chunks(db_session, sample_chapter):
    """Create sample chunks with embeddings for testing."""
    # Create sample embeddings (1536 dimensions - random but deterministic)
    import random
    random.seed(42)

    chunks = []
    for i in range(5):
        # Generate unique embedding for each chunk
        embedding = [random.random() for _ in range(1536)]

        chunk = Chunk(
            id=uuid4(),
            chapter_id=sample_chapter.id,
            content=f"This is chunk {i} about neural networks and deep learning. "
                   f"Neural networks consist of layers of neurons. "
                   f"Each neuron applies an activation function to its inputs.",
            embedding=embedding,
            chunk_index=i,
            section_title=f"Section {i}" if i > 0 else None,
            chunk_metadata={"page": i + 1},
            created_at=datetime.utcnow(),
        )
        db_session.add(chunk)
        chunks.append(chunk)

    await db_session.commit()
    return chunks


@pytest.mark.asyncio
async def test_retrieve_returns_relevant_chunks(db_session, sample_chunks):
    """Test that retrieve() returns relevant chunks."""
    rag_service = RAGService(db_session)

    # Query related to the chunk content
    query = "What are neural networks?"

    results = await rag_service.retrieve(
        query=query,
        top_k=3,
        similarity_threshold=0.0,  # Low threshold to ensure we get results
    )

    # Should return chunks
    assert len(results) > 0
    assert len(results) <= 3

    # Verify result structure
    for result in results:
        assert isinstance(result, RetrievedChunk)
        assert result.content is not None
        assert result.semantic_score >= 0.0
        assert result.semantic_score <= 1.0
        assert result.keyword_score >= 0.0
        assert result.combined_score >= 0.0
        assert result.chapter_title == "Introduction to Neural Networks"


@pytest.mark.asyncio
async def test_chapter_filtering_works(db_session, sample_book, sample_chunks):
    """Test that chapter filtering limits results to specific chapter."""
    # Create another chapter with chunks
    other_chapter = Chapter(
        id=uuid4(),
        book_id=sample_book.id,
        title="Advanced Topics",
        chapter_number=2,
        summary="Advanced topics",
        key_concepts=["advanced"],
        prerequisites=[],
        created_at=datetime.utcnow(),
    )
    db_session.add(other_chapter)

    # Add chunk to other chapter
    import random
    random.seed(99)
    embedding = [random.random() for _ in range(1536)]

    other_chunk = Chunk(
        id=uuid4(),
        chapter_id=other_chapter.id,
        content="This is from the advanced chapter about convolutional networks.",
        embedding=embedding,
        chunk_index=0,
        section_title=None,
        chunk_metadata={},
        created_at=datetime.utcnow(),
    )
    db_session.add(other_chunk)
    await db_session.commit()

    rag_service = RAGService(db_session)

    # Query with chapter filter
    chapter_id = sample_chunks[0].chapter_id
    results = await rag_service.retrieve(
        query="neural networks",
        chapter_id=chapter_id,
        top_k=10,
        similarity_threshold=0.0,
    )

    # All results should be from the specified chapter
    assert len(results) > 0
    for result in results:
        assert result.chapter_id == chapter_id
        assert result.chapter_title == "Introduction to Neural Networks"


@pytest.mark.asyncio
async def test_empty_results_handled_gracefully(db_session):
    """Test that empty results are handled gracefully."""
    rag_service = RAGService(db_session)

    # Query with no matching chunks (empty database or irrelevant query)
    results = await rag_service.retrieve(
        query="completely unrelated topic xyz123",
        top_k=5,
        similarity_threshold=0.99,  # Very high threshold
    )

    # Should return empty list, not crash
    assert results == []


@pytest.mark.asyncio
async def test_hybrid_search_combines_scores(db_session, sample_chunks):
    """Test that hybrid search combines semantic and keyword scores."""
    rag_service = RAGService(
        db_session, semantic_weight=0.7, keyword_weight=0.3
    )

    # Query that should match both semantically and by keyword
    query = "neural networks activation function"

    results = await rag_service.retrieve(
        query=query, top_k=3, similarity_threshold=0.0
    )

    assert len(results) > 0

    # Verify scores are combined
    for result in results:
        # Combined score should be weighted average
        expected_combined = (
            0.7 * result.semantic_score + 0.3 * result.keyword_score
        )
        # Allow small floating point error
        assert abs(result.combined_score - expected_combined) < 0.01


@pytest.mark.asyncio
async def test_reranking_adjusts_scores(db_session, sample_chunks):
    """Test that reranking adjusts chunk scores."""
    rag_service = RAGService(db_session)

    query = "neural networks"

    # Get results (which includes reranking)
    results = await rag_service.retrieve(
        query=query, top_k=3, similarity_threshold=0.0
    )

    assert len(results) > 0

    # Results should be sorted by combined score (descending)
    for i in range(len(results) - 1):
        assert results[i].combined_score >= results[i + 1].combined_score


@pytest.mark.asyncio
async def test_retrieve_with_context(db_session, sample_chapter, sample_chunks):
    """Test retrieve_with_context returns RAGContext with full metadata."""
    rag_service = RAGService(db_session)

    # Create sample conversation history
    conversation_id = uuid4()
    messages = [
        Message(
            id=uuid4(),
            conversation_id=conversation_id,
            role="user",
            content="What is a neural network?",
            created_at=datetime.utcnow(),
        ),
        Message(
            id=uuid4(),
            conversation_id=conversation_id,
            role="assistant",
            content="Let me help you understand neural networks...",
            created_at=datetime.utcnow(),
        ),
    ]

    # Test retrieve_with_context
    context = await rag_service.retrieve_with_context(
        query="Tell me about activation functions",
        chapter_id=sample_chapter.id,
        conversation_history=messages,
        top_k=3,
    )

    # Verify RAGContext structure
    assert isinstance(context, RAGContext)
    assert len(context.chunks) > 0
    assert len(context.chunks) <= 3

    # Verify chapter info
    assert context.chapter_info["chapter_title"] == "Introduction to Neural Networks"
    assert context.chapter_info["chapter_number"] == 1
    assert "neural networks" in context.chapter_info["key_concepts"]

    # Verify prerequisite chapters
    assert isinstance(context.prerequisite_chapters, list)
    # This chapter has no prerequisites
    assert len(context.prerequisite_chapters) == 0


@pytest.mark.asyncio
async def test_similarity_threshold_filters_results(db_session, sample_chunks):
    """Test that similarity threshold properly filters low-quality results."""
    rag_service = RAGService(db_session)

    query = "neural networks"

    # Get results with high threshold
    high_threshold_results = await rag_service.retrieve(
        query=query, top_k=10, similarity_threshold=0.8
    )

    # Get results with low threshold
    low_threshold_results = await rag_service.retrieve(
        query=query, top_k=10, similarity_threshold=0.0
    )

    # Low threshold should return more or equal results
    assert len(low_threshold_results) >= len(high_threshold_results)

    # All high threshold results should pass threshold
    for result in high_threshold_results:
        assert result.combined_score >= 0.8


@pytest.mark.asyncio
async def test_format_context_for_llm(db_session, sample_chunks):
    """Test formatting chunks into LLM context string."""
    rag_service = RAGService(db_session)

    query = "neural networks"
    results = await rag_service.retrieve(
        query=query, top_k=3, similarity_threshold=0.0
    )

    # Format for LLM
    context_string = await rag_service.format_context_for_llm(
        results, max_tokens=2000
    )

    # Verify context string structure
    assert "Relevant Context from Course Materials" in context_string
    assert "Source 1" in context_string
    assert "Test Book on Machine Learning" in context_string
    assert "neural networks" in context_string.lower()


@pytest.mark.asyncio
async def test_weights_must_sum_to_one():
    """Test that RAGService validates weights sum to 1.0."""
    from unittest.mock import MagicMock

    mock_session = MagicMock()

    # Valid weights
    rag_service = RAGService(
        mock_session, semantic_weight=0.6, keyword_weight=0.4
    )
    assert rag_service.semantic_weight == 0.6
    assert rag_service.keyword_weight == 0.4

    # Invalid weights should raise ValueError
    with pytest.raises(ValueError, match="must sum to 1.0"):
        RAGService(mock_session, semantic_weight=0.5, keyword_weight=0.3)


@pytest.mark.asyncio
async def test_empty_conversation_history_handled(db_session, sample_chapter, sample_chunks):
    """Test that empty conversation history is handled gracefully."""
    rag_service = RAGService(db_session)

    context = await rag_service.retrieve_with_context(
        query="What are neural networks?",
        chapter_id=sample_chapter.id,
        conversation_history=[],
        top_k=3,
    )

    # Should still work with empty history
    assert isinstance(context, RAGContext)
    assert len(context.chunks) > 0
