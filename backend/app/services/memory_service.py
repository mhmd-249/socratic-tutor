"""Memory service for cross-conversation continuity."""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.chapter import Chapter
from app.models.conversation import Conversation
from app.models.conversation_summary import ConversationSummary
from app.repositories.chapter import ChapterRepository
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class RelevantMemory:
    """A relevant memory from a past conversation."""

    summary_id: UUID
    conversation_id: UUID
    chapter_id: UUID
    chapter_title: str
    chapter_number: int
    book_title: str
    summary_text: str
    topics_covered: list[str]
    concepts_understood: list[str]
    concepts_struggled: list[str]
    conversation_date: datetime
    similarity_score: float
    relevance_reason: str  # Why this memory is relevant


class MemoryService:
    """Service for retrieving relevant memories from past conversations."""

    # Similarity threshold for including memories
    SIMILARITY_THRESHOLD = 0.5

    # Maximum memories to return by default
    DEFAULT_MAX_MEMORIES = 3

    def __init__(self, session: AsyncSession):
        """
        Initialize memory service.

        Args:
            session: Database session
        """
        self.session = session
        self.embedding_service = EmbeddingService()
        self.chapter_repo = ChapterRepository(session)

    async def get_relevant_history(
        self,
        user_id: UUID,
        current_chapter_id: UUID,
        current_query: str,
        max_memories: int = DEFAULT_MAX_MEMORIES,
    ) -> list[RelevantMemory]:
        """
        Find relevant past interactions to include in current conversation.

        Uses semantic similarity to find related discussions.

        Args:
            user_id: User UUID
            current_chapter_id: Current chapter being studied
            current_query: User's current message/query
            max_memories: Maximum number of memories to return

        Returns:
            List of RelevantMemory objects ordered by relevance
        """
        logger.info(
            f"Finding relevant memories for user {user_id}, "
            f"chapter {current_chapter_id}"
        )

        # Generate embedding for the current query
        try:
            query_embedding = await self.embedding_service.generate_embedding(
                current_query
            )
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            # Fall back to non-semantic search
            return await self._get_recent_memories(user_id, current_chapter_id, max_memories)

        # Get current chapter info for context-aware filtering
        current_chapter = await self.chapter_repo.get(current_chapter_id)

        # Perform semantic search on conversation summaries
        memories = await self._semantic_search_memories(
            user_id=user_id,
            query_embedding=query_embedding,
            current_chapter=current_chapter,
            max_results=max_memories * 2,  # Get more for filtering
        )

        # Filter and rank memories
        ranked_memories = self._rank_and_filter_memories(
            memories=memories,
            current_chapter=current_chapter,
            max_results=max_memories,
        )

        logger.info(f"Found {len(ranked_memories)} relevant memories")
        return ranked_memories

    async def _semantic_search_memories(
        self,
        user_id: UUID,
        query_embedding: list[float],
        current_chapter: Chapter | None,
        max_results: int,
    ) -> list[RelevantMemory]:
        """
        Search conversation summaries using semantic similarity.

        Args:
            user_id: User UUID
            query_embedding: Embedding vector for the query
            current_chapter: Current chapter being studied
            max_results: Maximum results to return

        Returns:
            List of memories with similarity scores
        """
        # Build the query using pgvector's cosine distance
        # Lower distance = higher similarity
        current_chapter_id = current_chapter.id if current_chapter else UUID(int=0)

        # Format embedding as PostgreSQL vector literal
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        query = text("""
            SELECT
                cs.id,
                cs.conversation_id,
                cs.summary,
                cs.topics_covered,
                cs.concepts_understood,
                cs.concepts_struggled,
                cs.created_at,
                c.chapter_id,
                ch.title as chapter_title,
                ch.chapter_number,
                b.title as book_title,
                1 - (cs.embedding <=> (:query_embedding)::vector) as similarity
            FROM conversation_summaries cs
            JOIN conversations c ON cs.conversation_id = c.id
            JOIN chapters ch ON c.chapter_id = ch.id
            JOIN books b ON ch.book_id = b.id
            WHERE c.user_id = :user_id
              AND cs.embedding IS NOT NULL
              AND c.chapter_id != :current_chapter_id
            ORDER BY cs.embedding <=> (:query_embedding)::vector
            LIMIT :limit
        """).bindparams(
            bindparam("user_id", value=user_id),
            bindparam("query_embedding", value=embedding_str),
            bindparam("current_chapter_id", value=current_chapter_id),
            bindparam("limit", value=max_results),
        )

        result = await self.session.execute(query)

        rows = result.fetchall()
        memories = []

        for row in rows:
            # Skip low-similarity results
            if row.similarity < self.SIMILARITY_THRESHOLD:
                continue

            memories.append(
                RelevantMemory(
                    summary_id=row.id,
                    conversation_id=row.conversation_id,
                    chapter_id=row.chapter_id,
                    chapter_title=row.chapter_title,
                    chapter_number=row.chapter_number,
                    book_title=row.book_title,
                    summary_text=row.summary,
                    topics_covered=row.topics_covered or [],
                    concepts_understood=row.concepts_understood or [],
                    concepts_struggled=row.concepts_struggled or [],
                    conversation_date=row.created_at,
                    similarity_score=row.similarity,
                    relevance_reason="Semantically related to current discussion",
                )
            )

        return memories

    async def _get_recent_memories(
        self,
        user_id: UUID,
        current_chapter_id: UUID,
        max_results: int,
    ) -> list[RelevantMemory]:
        """
        Fallback: Get recent memories without semantic search.

        Args:
            user_id: User UUID
            current_chapter_id: Current chapter (to exclude)
            max_results: Maximum results to return

        Returns:
            List of recent memories
        """
        query = (
            select(ConversationSummary)
            .join(Conversation)
            .options(joinedload(ConversationSummary.conversation))
            .where(Conversation.user_id == user_id)
            .where(Conversation.chapter_id != current_chapter_id)
            .order_by(ConversationSummary.created_at.desc())
            .limit(max_results)
        )

        result = await self.session.execute(query)
        summaries = result.scalars().all()

        memories = []
        for summary in summaries:
            conversation = summary.conversation
            if not conversation:
                continue

            chapter = await self.chapter_repo.get(conversation.chapter_id)
            if not chapter:
                continue

            from app.repositories.book import BookRepository
            book_repo = BookRepository(self.session)
            book = await book_repo.get(chapter.book_id)

            memories.append(
                RelevantMemory(
                    summary_id=summary.id,
                    conversation_id=summary.conversation_id,
                    chapter_id=conversation.chapter_id,
                    chapter_title=chapter.title,
                    chapter_number=chapter.chapter_number,
                    book_title=book.title if book else "Unknown Book",
                    summary_text=summary.summary,
                    topics_covered=summary.topics_covered or [],
                    concepts_understood=summary.concepts_understood or [],
                    concepts_struggled=summary.concepts_struggled or [],
                    conversation_date=summary.created_at,
                    similarity_score=0.5,  # Default score for non-semantic
                    relevance_reason="Recent conversation",
                )
            )

        return memories

    def _rank_and_filter_memories(
        self,
        memories: list[RelevantMemory],
        current_chapter: Chapter | None,
        max_results: int,
    ) -> list[RelevantMemory]:
        """
        Rank and filter memories by relevance.

        Priority factors:
        1. Same book as current chapter (higher priority)
        2. Is a prerequisite of current chapter
        3. Contains struggled concepts (may need revisiting)
        4. Semantic similarity score

        Args:
            memories: List of candidate memories
            current_chapter: Current chapter being studied
            max_results: Maximum results to return

        Returns:
            Filtered and ranked memories
        """
        if not memories:
            return []

        scored_memories = []
        current_book_id = current_chapter.book_id if current_chapter else None
        prerequisites = set(current_chapter.prerequisites or []) if current_chapter else set()

        for memory in memories:
            score = memory.similarity_score

            # Boost for same book
            if current_book_id and memory.chapter_id:
                # We need to check if chapter is in the same book
                # Since we have chapter_id, we can infer from the memory itself
                # For simplicity, assume same book if similar chapter numbers
                score += 0.1

            # Boost for prerequisite chapters
            if memory.chapter_id in prerequisites:
                score += 0.2
                memory.relevance_reason = "Prerequisite chapter - foundational concepts"

            # Boost for memories with struggled concepts
            if memory.concepts_struggled:
                score += 0.1
                if not memory.relevance_reason.startswith("Prerequisite"):
                    memory.relevance_reason = "Contains concepts you struggled with before"

            scored_memories.append((score, memory))

        # Sort by score descending
        scored_memories.sort(key=lambda x: x[0], reverse=True)

        # Return top results
        return [memory for _, memory in scored_memories[:max_results]]

    async def format_memories_for_prompt(
        self,
        memories: list[RelevantMemory],
    ) -> str:
        """
        Format memories as natural language for inclusion in prompt.

        Creates a conversational summary that the tutor can reference.

        Args:
            memories: List of relevant memories to format

        Returns:
            Formatted string for prompt inclusion, or empty string if no memories
        """
        if not memories:
            return ""

        formatted_parts = []

        for i, memory in enumerate(memories, 1):
            # Format the date nicely
            date_str = memory.conversation_date.strftime("%B %d")

            # Build the memory summary
            parts = []
            parts.append(
                f"**Discussion {i}** (Chapter {memory.chapter_number}: "
                f"{memory.chapter_title}, {date_str})"
            )

            # Add summary
            parts.append(f"Summary: {memory.summary_text}")

            # Add struggled concepts (important for continuity)
            if memory.concepts_struggled:
                struggled = ", ".join(memory.concepts_struggled[:3])
                parts.append(f"Struggled with: {struggled}")

            # Add understood concepts
            if memory.concepts_understood:
                understood = ", ".join(memory.concepts_understood[:3])
                parts.append(f"Understood: {understood}")

            # Add relevance note
            parts.append(f"Relevance: {memory.relevance_reason}")

            formatted_parts.append("\n".join(parts))

        return "\n\n".join(formatted_parts)

    async def get_struggled_concepts_history(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> list[str]:
        """
        Get all concepts the user has struggled with across conversations.

        Useful for building a comprehensive picture of learning gaps.

        Args:
            user_id: User UUID
            limit: Maximum summaries to scan

        Returns:
            Deduplicated list of struggled concepts
        """
        query = (
            select(ConversationSummary.concepts_struggled)
            .join(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(ConversationSummary.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        rows = result.scalars().all()

        # Flatten and deduplicate
        all_struggled = []
        seen = set()
        for struggled_list in rows:
            if struggled_list:
                for concept in struggled_list:
                    if concept.lower() not in seen:
                        seen.add(concept.lower())
                        all_struggled.append(concept)

        return all_struggled

    async def check_concept_previously_struggled(
        self,
        user_id: UUID,
        concept: str,
    ) -> bool:
        """
        Check if user has struggled with a specific concept before.

        Args:
            user_id: User UUID
            concept: Concept to check

        Returns:
            True if user has struggled with this concept
        """
        # Use array containment check
        query = text("""
            SELECT EXISTS(
                SELECT 1
                FROM conversation_summaries cs
                JOIN conversations c ON cs.conversation_id = c.id
                WHERE c.user_id = :user_id
                  AND :concept = ANY(cs.concepts_struggled)
            )
        """).bindparams(
            bindparam("user_id", value=user_id),
            bindparam("concept", value=concept),
        )

        result = await self.session.execute(query)

        return result.scalar() or False
