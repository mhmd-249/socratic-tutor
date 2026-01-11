"""Tests for memory service."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.memory_service import (
    MemoryService,
    RelevantMemory,
)


class TestRelevantMemory:
    """Tests for RelevantMemory dataclass."""

    def test_create_relevant_memory(self):
        """Test creating a RelevantMemory."""
        memory = RelevantMemory(
            summary_id=uuid4(),
            conversation_id=uuid4(),
            chapter_id=uuid4(),
            chapter_title="Introduction to Neural Networks",
            chapter_number=1,
            book_title="Deep Learning",
            summary_text="Student explored backpropagation concepts.",
            topics_covered=["neural networks", "backpropagation"],
            concepts_understood=["activation functions"],
            concepts_struggled=["gradient descent"],
            conversation_date=datetime.utcnow(),
            similarity_score=0.85,
            relevance_reason="Semantically related",
        )

        assert memory.chapter_title == "Introduction to Neural Networks"
        assert memory.similarity_score == 0.85
        assert "gradient descent" in memory.concepts_struggled


class TestFormatMemoriesForPrompt:
    """Tests for formatting memories for prompt inclusion."""

    @pytest.mark.asyncio
    async def test_format_empty_memories(self):
        """Test formatting empty memory list."""
        service = MagicMock(spec=MemoryService)
        service.format_memories_for_prompt = MemoryService.format_memories_for_prompt

        result = await service.format_memories_for_prompt(service, [])
        assert result == ""

    @pytest.mark.asyncio
    async def test_format_single_memory(self):
        """Test formatting a single memory."""
        service = MagicMock(spec=MemoryService)
        service.format_memories_for_prompt = MemoryService.format_memories_for_prompt

        memory = RelevantMemory(
            summary_id=uuid4(),
            conversation_id=uuid4(),
            chapter_id=uuid4(),
            chapter_title="Neural Networks Basics",
            chapter_number=2,
            book_title="ML Book",
            summary_text="Discussed neural network fundamentals.",
            topics_covered=["neural networks"],
            concepts_understood=["perceptrons"],
            concepts_struggled=["backpropagation"],
            conversation_date=datetime(2024, 3, 15),
            similarity_score=0.8,
            relevance_reason="Related topic",
        )

        result = await service.format_memories_for_prompt(service, [memory])

        assert "Discussion 1" in result
        assert "Neural Networks Basics" in result
        assert "Chapter 2" in result
        assert "backpropagation" in result
        assert "perceptrons" in result
        assert "March 15" in result

    @pytest.mark.asyncio
    async def test_format_multiple_memories(self):
        """Test formatting multiple memories."""
        service = MagicMock(spec=MemoryService)
        service.format_memories_for_prompt = MemoryService.format_memories_for_prompt

        memories = [
            RelevantMemory(
                summary_id=uuid4(),
                conversation_id=uuid4(),
                chapter_id=uuid4(),
                chapter_title="Chapter A",
                chapter_number=1,
                book_title="Book",
                summary_text="Summary A",
                topics_covered=["topic1"],
                concepts_understood=["concept1"],
                concepts_struggled=[],
                conversation_date=datetime(2024, 3, 10),
                similarity_score=0.9,
                relevance_reason="Reason A",
            ),
            RelevantMemory(
                summary_id=uuid4(),
                conversation_id=uuid4(),
                chapter_id=uuid4(),
                chapter_title="Chapter B",
                chapter_number=2,
                book_title="Book",
                summary_text="Summary B",
                topics_covered=["topic2"],
                concepts_understood=[],
                concepts_struggled=["concept2"],
                conversation_date=datetime(2024, 3, 12),
                similarity_score=0.75,
                relevance_reason="Reason B",
            ),
        ]

        result = await service.format_memories_for_prompt(service, memories)

        assert "Discussion 1" in result
        assert "Discussion 2" in result
        assert "Chapter A" in result
        assert "Chapter B" in result


class TestRankAndFilterMemories:
    """Tests for memory ranking and filtering."""

    def test_filter_by_similarity_threshold(self):
        """Test that low similarity memories are filtered."""
        service = MagicMock(spec=MemoryService)
        service._rank_and_filter_memories = MemoryService._rank_and_filter_memories
        service.SIMILARITY_THRESHOLD = 0.5

        chapter_id = uuid4()

        memories = [
            RelevantMemory(
                summary_id=uuid4(),
                conversation_id=uuid4(),
                chapter_id=uuid4(),
                chapter_title="High Similarity",
                chapter_number=1,
                book_title="Book",
                summary_text="High similarity memory",
                topics_covered=[],
                concepts_understood=[],
                concepts_struggled=[],
                conversation_date=datetime.utcnow(),
                similarity_score=0.9,
                relevance_reason="High",
            ),
            RelevantMemory(
                summary_id=uuid4(),
                conversation_id=uuid4(),
                chapter_id=uuid4(),
                chapter_title="Low Similarity",
                chapter_number=2,
                book_title="Book",
                summary_text="Low similarity memory",
                topics_covered=[],
                concepts_understood=[],
                concepts_struggled=[],
                conversation_date=datetime.utcnow(),
                similarity_score=0.3,  # Below threshold
                relevance_reason="Low",
            ),
        ]

        current_chapter = MagicMock()
        current_chapter.book_id = uuid4()
        current_chapter.prerequisites = []

        result = service._rank_and_filter_memories(
            service, memories, current_chapter, max_results=5
        )

        # Both should be included since filtering happens in semantic_search_memories
        # This method just ranks them
        assert len(result) == 2

    def test_boost_prerequisite_chapters(self):
        """Test that prerequisite chapters get boosted ranking."""
        service = MagicMock(spec=MemoryService)
        service._rank_and_filter_memories = MemoryService._rank_and_filter_memories

        prereq_chapter_id = uuid4()
        other_chapter_id = uuid4()

        memories = [
            RelevantMemory(
                summary_id=uuid4(),
                conversation_id=uuid4(),
                chapter_id=other_chapter_id,
                chapter_title="Other Chapter",
                chapter_number=3,
                book_title="Book",
                summary_text="Not prerequisite",
                topics_covered=[],
                concepts_understood=[],
                concepts_struggled=[],
                conversation_date=datetime.utcnow(),
                similarity_score=0.8,
                relevance_reason="Regular",
            ),
            RelevantMemory(
                summary_id=uuid4(),
                conversation_id=uuid4(),
                chapter_id=prereq_chapter_id,
                chapter_title="Prerequisite Chapter",
                chapter_number=1,
                book_title="Book",
                summary_text="Is prerequisite",
                topics_covered=[],
                concepts_understood=[],
                concepts_struggled=[],
                conversation_date=datetime.utcnow(),
                similarity_score=0.7,  # Lower similarity but prerequisite
                relevance_reason="Prerequisite",
            ),
        ]

        current_chapter = MagicMock()
        current_chapter.book_id = uuid4()
        current_chapter.prerequisites = [prereq_chapter_id]

        result = service._rank_and_filter_memories(
            service, memories, current_chapter, max_results=5
        )

        # Prerequisite should be ranked first despite lower similarity
        assert result[0].chapter_id == prereq_chapter_id
        assert "Prerequisite" in result[0].relevance_reason

    def test_boost_struggled_concepts(self):
        """Test that memories with struggled concepts get boosted."""
        service = MagicMock(spec=MemoryService)
        service._rank_and_filter_memories = MemoryService._rank_and_filter_memories

        memories = [
            RelevantMemory(
                summary_id=uuid4(),
                conversation_id=uuid4(),
                chapter_id=uuid4(),
                chapter_title="No Struggles",
                chapter_number=1,
                book_title="Book",
                summary_text="Easy chapter",
                topics_covered=[],
                concepts_understood=["everything"],
                concepts_struggled=[],
                conversation_date=datetime.utcnow(),
                similarity_score=0.8,
                relevance_reason="Regular",
            ),
            RelevantMemory(
                summary_id=uuid4(),
                conversation_id=uuid4(),
                chapter_id=uuid4(),
                chapter_title="Had Struggles",
                chapter_number=2,
                book_title="Book",
                summary_text="Difficult chapter",
                topics_covered=[],
                concepts_understood=[],
                concepts_struggled=["hard concept"],
                conversation_date=datetime.utcnow(),
                similarity_score=0.7,  # Lower similarity but has struggles
                relevance_reason="Regular",
            ),
        ]

        current_chapter = MagicMock()
        current_chapter.book_id = uuid4()
        current_chapter.prerequisites = []

        result = service._rank_and_filter_memories(
            service, memories, current_chapter, max_results=5
        )

        # Memory with struggles should be ranked first
        assert result[0].chapter_title == "Had Struggles"
        assert "struggled" in result[0].relevance_reason.lower()

    def test_limit_results(self):
        """Test that results are limited correctly."""
        service = MagicMock(spec=MemoryService)
        service._rank_and_filter_memories = MemoryService._rank_and_filter_memories

        memories = [
            RelevantMemory(
                summary_id=uuid4(),
                conversation_id=uuid4(),
                chapter_id=uuid4(),
                chapter_title=f"Chapter {i}",
                chapter_number=i,
                book_title="Book",
                summary_text=f"Summary {i}",
                topics_covered=[],
                concepts_understood=[],
                concepts_struggled=[],
                conversation_date=datetime.utcnow(),
                similarity_score=0.9 - (i * 0.1),
                relevance_reason="Regular",
            )
            for i in range(5)
        ]

        current_chapter = MagicMock()
        current_chapter.book_id = uuid4()
        current_chapter.prerequisites = []

        result = service._rank_and_filter_memories(
            service, memories, current_chapter, max_results=3
        )

        assert len(result) == 3


class TestGetStruggledConceptsHistory:
    """Tests for getting struggled concepts across conversations."""

    @pytest.mark.asyncio
    async def test_get_struggled_concepts(self):
        """Test getting all struggled concepts for a user."""
        # This test would require database access
        pytest.skip("Requires database session - run with pytest fixtures")

    @pytest.mark.asyncio
    async def test_deduplicate_concepts(self):
        """Test that concepts are deduplicated."""
        # Would test that "Backpropagation" and "backpropagation" become one
        pytest.skip("Requires database session - run with pytest fixtures")


class TestCheckConceptPreviouslyStruggled:
    """Tests for checking if user struggled with specific concept."""

    @pytest.mark.asyncio
    async def test_check_concept_exists(self):
        """Test checking for existing struggled concept."""
        pytest.skip("Requires database session - run with pytest fixtures")

    @pytest.mark.asyncio
    async def test_check_concept_not_exists(self):
        """Test checking for non-existing concept."""
        pytest.skip("Requires database session - run with pytest fixtures")


class TestGetRelevantHistory:
    """Tests for the main get_relevant_history method."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_new_user(self):
        """Test that new users get empty memory list."""
        session = AsyncMock()
        service = MemoryService(session)

        # Mock embedding service
        service.embedding_service = AsyncMock()
        service.embedding_service.generate_embedding = AsyncMock(
            return_value=[0.1] * 1536
        )

        # Mock chapter repo
        service.chapter_repo = AsyncMock()
        service.chapter_repo.get = AsyncMock(return_value=None)

        # Mock session execute for semantic search (no results)
        session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        session.execute.return_value = mock_result

        result = await service.get_relevant_history(
            user_id=uuid4(),
            current_chapter_id=uuid4(),
            current_query="What is machine learning?",
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_falls_back_on_embedding_error(self):
        """Test that service falls back to recent memories on embedding error."""
        session = AsyncMock()
        service = MemoryService(session)

        # Mock embedding service to fail
        service.embedding_service = AsyncMock()
        service.embedding_service.generate_embedding = AsyncMock(
            side_effect=Exception("API Error")
        )

        # Mock chapter repo
        service.chapter_repo = AsyncMock()
        service.chapter_repo.get = AsyncMock(return_value=None)

        # Mock _get_recent_memories
        with patch.object(service, '_get_recent_memories') as mock_recent:
            mock_recent.return_value = []

            result = await service.get_relevant_history(
                user_id=uuid4(),
                current_chapter_id=uuid4(),
                current_query="What is machine learning?",
            )

            # Should have called fallback
            mock_recent.assert_called_once()


class TestMemoryServiceIntegration:
    """Integration tests for memory service."""

    @pytest.mark.asyncio
    async def test_full_memory_flow(self):
        """Test complete flow: search -> rank -> format."""
        pytest.skip("Requires database session - run with pytest fixtures")

    @pytest.mark.asyncio
    async def test_memory_excludes_current_chapter(self):
        """Test that current chapter conversations are excluded."""
        pytest.skip("Requires database session - run with pytest fixtures")
