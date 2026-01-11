"""RAG (Retrieval-Augmented Generation) service with hybrid search."""

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.message import Message
from app.repositories.book import BookRepository
from app.repositories.chapter import ChapterRepository
from app.repositories.chunk import ChunkRepository
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """Container for retrieved chunk with metadata and scores."""

    chunk_id: UUID
    content: str
    section_title: str | None
    chunk_index: int
    semantic_score: float  # 0-1, from cosine similarity
    keyword_score: float  # 0-1, from full-text search rank
    combined_score: float  # Weighted combination
    chapter_id: UUID
    chapter_title: str
    chapter_number: int
    book_title: str
    book_author: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "chunk_id": str(self.chunk_id),
            "content": self.content,
            "section_title": self.section_title,
            "chunk_index": self.chunk_index,
            "semantic_score": self.semantic_score,
            "keyword_score": self.keyword_score,
            "combined_score": self.combined_score,
            "chapter_title": self.chapter_title,
            "chapter_number": self.chapter_number,
            "book_title": self.book_title,
        }

    def to_context_string(self) -> str:
        """Format chunk as context string for LLM."""
        source = f"[{self.book_title} - Chapter {self.chapter_number}: {self.chapter_title}"
        if self.section_title:
            source += f" - {self.section_title}"
        source += "]"
        return f"{source}\n{self.content}"


@dataclass
class RAGContext:
    """Complete RAG context with chunks, chapter info, and prerequisites."""

    chunks: list[RetrievedChunk]
    chapter_info: dict[str, Any]
    prerequisite_chapters: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "chapter_info": self.chapter_info,
            "prerequisite_chapters": self.prerequisite_chapters,
        }


class RAGService:
    """Service for retrieving relevant context using hybrid search."""

    def __init__(
        self,
        session: AsyncSession,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ):
        """
        Initialize RAG service.

        Args:
            session: Database session
            semantic_weight: Weight for semantic search score (default: 0.7)
            keyword_weight: Weight for keyword search score (default: 0.3)
        """
        self.session = session
        self.embedding_service = EmbeddingService()
        self.chunk_repo = ChunkRepository(session)
        self.chapter_repo = ChapterRepository(session)
        self.book_repo = BookRepository(session)
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight

        # Validate weights sum to 1.0
        if abs((semantic_weight + keyword_weight) - 1.0) > 0.01:
            raise ValueError("Semantic and keyword weights must sum to 1.0")

    async def get_chapter_context(self, chapter_id: UUID) -> dict[str, Any]:
        """
        Get chapter context information without retrieving chunks.

        Used when starting a new conversation to get chapter details
        for the initial greeting.

        Args:
            chapter_id: Chapter UUID

        Returns:
            Dictionary with chapter and book information

        Raises:
            ValueError: If chapter or book not found
        """
        logger.info(f"Getting chapter context for chapter {chapter_id}")

        # Get chapter information
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")

        book = await self.book_repo.get(chapter.book_id)
        if not book:
            raise ValueError(f"Book {chapter.book_id} not found")

        chapter_info = {
            "chapter_id": str(chapter.id),
            "chapter_title": chapter.title,
            "chapter_number": chapter.chapter_number,
            "summary": chapter.summary,
            "key_concepts": chapter.key_concepts,
            "book_title": book.title,
            "book_author": book.author,
        }

        logger.info(f"Retrieved chapter context: {chapter.title}")
        return chapter_info

    async def retrieve(
        self,
        query: str,
        chapter_id: UUID | None = None,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
    ) -> list[RetrievedChunk]:
        """
        Retrieve relevant chunks using hybrid search.

        Combines semantic search (pgvector) and keyword search (full-text)
        with configurable weights.

        Args:
            query: User's question or search query
            chapter_id: Optional chapter to limit search to
            top_k: Maximum number of chunks to retrieve
            similarity_threshold: Minimum combined score threshold (0-1)

        Returns:
            List of retrieved chunks sorted by combined score (descending)
        """
        logger.info(
            f"Retrieving top {top_k} chunks for query: '{query[:100]}...'"
        )
        logger.debug(
            f"Semantic weight: {self.semantic_weight}, "
            f"Keyword weight: {self.keyword_weight}, "
            f"Threshold: {similarity_threshold}"
        )

        # Generate query embedding for semantic search
        query_embedding = await self.embedding_service.generate_embedding(query)

        # Perform hybrid search
        results = await self._hybrid_search(
            query=query,
            query_embedding=query_embedding,
            chapter_id=chapter_id,
            limit=top_k * 2,  # Retrieve more for reranking
        )

        # Filter by threshold
        filtered_results = [
            r for r in results if r.combined_score >= similarity_threshold
        ]

        logger.info(
            f"Retrieved {len(filtered_results)} chunks above threshold "
            f"(from {len(results)} total candidates)"
        )

        # Rerank results (optional but recommended)
        reranked_results = await self._rerank(filtered_results, query)

        # Return top_k results
        final_results = reranked_results[:top_k]

        logger.info(f"Returning top {len(final_results)} chunks after reranking")
        return final_results

    async def retrieve_with_context(
        self,
        query: str,
        chapter_id: UUID,
        conversation_history: list[Message],
        top_k: int = 5,
    ) -> RAGContext:
        """
        Retrieve chunks considering conversation context.

        Returns chunks + chapter info + relevant prerequisites.

        Args:
            query: User's current question
            chapter_id: Current chapter being studied
            conversation_history: Recent messages from conversation
            top_k: Maximum number of chunks to retrieve

        Returns:
            RAGContext with chunks, chapter info, and prerequisites
        """
        logger.info(
            f"Retrieving context with conversation history "
            f"({len(conversation_history)} messages)"
        )

        # Enhance query with conversation context
        enhanced_query = self._enhance_query_with_history(
            query, conversation_history
        )

        # Retrieve chunks using enhanced query
        chunks = await self.retrieve(
            query=enhanced_query,
            chapter_id=chapter_id,
            top_k=top_k,
            similarity_threshold=0.5,  # Lower threshold for conversational context
        )

        # Get chapter information
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")

        book = await self.book_repo.get(chapter.book_id)
        if not book:
            raise ValueError(f"Book {chapter.book_id} not found")

        chapter_info = {
            "chapter_id": str(chapter.id),
            "chapter_title": chapter.title,
            "chapter_number": chapter.chapter_number,
            "summary": chapter.summary,
            "key_concepts": chapter.key_concepts,
            "book_title": book.title,
            "book_author": book.author,
        }

        # Get prerequisite chapters
        prerequisite_chapters = []
        if chapter.prerequisites:
            for prereq_id in chapter.prerequisites:
                prereq = await self.chapter_repo.get(UUID(prereq_id))
                if prereq:
                    prerequisite_chapters.append(
                        {
                            "chapter_id": str(prereq.id),
                            "chapter_title": prereq.title,
                            "chapter_number": prereq.chapter_number,
                        }
                    )

        logger.info(
            f"Retrieved context: {len(chunks)} chunks, "
            f"{len(prerequisite_chapters)} prerequisites"
        )

        return RAGContext(
            chunks=chunks,
            chapter_info=chapter_info,
            prerequisite_chapters=prerequisite_chapters,
        )

    async def _hybrid_search(
        self,
        query: str,
        query_embedding: list[float],
        chapter_id: UUID | None,
        limit: int,
    ) -> list[RetrievedChunk]:
        """
        Perform hybrid search combining semantic and keyword search.

        Args:
            query: Search query string
            query_embedding: Query embedding vector
            chapter_id: Optional chapter to filter by
            limit: Maximum results to return

        Returns:
            List of retrieved chunks with scores
        """
        # Convert embedding to PostgreSQL vector format
        # Safe to interpolate since it's internally generated, not user input
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        # Build hybrid search query
        # Uses RRF (Reciprocal Rank Fusion) style scoring:
        # - Semantic: cosine similarity via <=> operator
        # - Keyword: ts_rank from full-text search
        # - Combine with weighted average

        # Build chapter filter for SQL
        if chapter_id:
            chapter_filter_sql = f"AND c.chapter_id = '{str(chapter_id)}'"
        else:
            chapter_filter_sql = ""

        # Build SQL query with direct embedding interpolation
        # Using f-string for embedding and chapter_id (both safe - not user input)
        # Using named parameters for user input (query) and numeric params
        query_sql = text(f"""
            WITH semantic_scores AS (
                SELECT
                    c.id,
                    c.chapter_id,
                    c.content,
                    c.section_title,
                    c.chunk_index,
                    1 - (c.embedding <=> '{embedding_str}'::vector) as semantic_score
                FROM chunks c
                WHERE true {chapter_filter_sql}
            ),
            keyword_scores AS (
                SELECT
                    c.id,
                    ts_rank(c.content_tsv, websearch_to_tsquery('english', :query)) as keyword_score
                FROM chunks c
                WHERE c.content_tsv @@ websearch_to_tsquery('english', :query)
                    {chapter_filter_sql}
            ),
            combined AS (
                SELECT
                    s.id,
                    s.chapter_id,
                    s.content,
                    s.section_title,
                    s.chunk_index,
                    s.semantic_score,
                    COALESCE(k.keyword_score, 0.0) as keyword_score,
                    (:semantic_weight * s.semantic_score +
                     :keyword_weight * COALESCE(k.keyword_score, 0.0)) as combined_score
                FROM semantic_scores s
                LEFT JOIN keyword_scores k ON s.id = k.id
            )
            SELECT
                c.id,
                c.chapter_id,
                c.content,
                c.section_title,
                c.chunk_index,
                c.semantic_score,
                c.keyword_score,
                c.combined_score,
                ch.title as chapter_title,
                ch.chapter_number,
                b.title as book_title,
                b.author as book_author
            FROM combined c
            INNER JOIN chapters ch ON c.chapter_id = ch.id
            INNER JOIN books b ON ch.book_id = b.id
            ORDER BY c.combined_score DESC
            LIMIT :limit
        """).bindparams(
            bindparam("query", value=query),
            bindparam("semantic_weight", value=self.semantic_weight),
            bindparam("keyword_weight", value=self.keyword_weight),
            bindparam("limit", value=limit),
        )

        # Execute with bound parameters (SQLAlchemy with asyncpg)
        result = await self.session.execute(query_sql)
        rows = result.fetchall()

        retrieved_chunks = []
        for row in rows:
            chunk = RetrievedChunk(
                chunk_id=row.id,
                content=row.content,
                section_title=row.section_title,
                chunk_index=row.chunk_index,
                semantic_score=float(row.semantic_score),
                keyword_score=float(row.keyword_score),
                combined_score=float(row.combined_score),
                chapter_id=row.chapter_id,
                chapter_title=row.chapter_title,
                chapter_number=row.chapter_number,
                book_title=row.book_title,
                book_author=row.book_author,
            )
            retrieved_chunks.append(chunk)

            logger.debug(
                f"Chunk {row.chunk_index}: semantic={row.semantic_score:.3f}, "
                f"keyword={row.keyword_score:.3f}, combined={row.combined_score:.3f}"
            )

        return retrieved_chunks

    async def _rerank(
        self, chunks: list[RetrievedChunk], query: str
    ) -> list[RetrievedChunk]:
        """
        Rerank chunks using heuristic scoring.

        Considers:
        - Original combined score (primary)
        - Query term overlap (boost)
        - Chunk position in chapter (slight preference for earlier chunks)

        Args:
            chunks: Initial retrieved chunks
            query: Original query

        Returns:
            Reranked chunks
        """
        if not chunks:
            return chunks

        logger.debug(f"Reranking {len(chunks)} chunks")

        # Extract query terms (simple tokenization)
        query_terms = set(query.lower().split())

        for chunk in chunks:
            # Count query term matches in content
            content_lower = chunk.content.lower()
            term_matches = sum(
                1 for term in query_terms if term in content_lower
            )

            # Normalize term match score (0-1)
            term_match_score = min(term_matches / max(len(query_terms), 1), 1.0)

            # Position score: slight preference for earlier chunks (0.9-1.0)
            position_score = 1.0 - (chunk.chunk_index * 0.01)
            position_score = max(position_score, 0.9)

            # Rerank score combines original score with boosts
            rerank_score = (
                chunk.combined_score * 0.8  # Original score (80%)
                + term_match_score * 0.15  # Term matches (15%)
                + position_score * 0.05  # Position (5%)
            )

            # Update combined score with reranked score
            chunk.combined_score = rerank_score

            logger.debug(
                f"Chunk {chunk.chunk_index}: "
                f"original={chunk.combined_score:.3f}, "
                f"terms={term_match_score:.3f}, "
                f"position={position_score:.3f}, "
                f"reranked={rerank_score:.3f}"
            )

        # Sort by new combined score
        chunks.sort(key=lambda x: x.combined_score, reverse=True)

        return chunks

    def _enhance_query_with_history(
        self, query: str, conversation_history: list[Message]
    ) -> str:
        """
        Enhance query with conversation context.

        Extracts key topics from recent messages to provide better context.

        Args:
            query: Current user query
            conversation_history: Recent conversation messages

        Returns:
            Enhanced query string
        """
        if not conversation_history:
            return query

        # Take last 3 user messages for context (excluding current)
        recent_user_messages = [
            msg.content
            for msg in conversation_history[-6:]
            if msg.role == "user"
        ][-3:]

        if not recent_user_messages:
            return query

        # Simple enhancement: append recent topics
        # In production, could use LLM to generate better reformulation
        context_terms = " ".join(recent_user_messages[-2:])  # Last 2 messages

        enhanced = f"{query} {context_terms}"

        logger.debug(f"Enhanced query: '{query}' -> '{enhanced[:100]}...'")

        return enhanced

    async def format_context_for_llm(
        self, chunks: list[RetrievedChunk], max_tokens: int = 4000
    ) -> str:
        """
        Format retrieved chunks into context string for LLM.

        Args:
            chunks: Retrieved chunks
            max_tokens: Maximum token budget for context

        Returns:
            Formatted context string
        """
        if not chunks:
            return "No relevant context found in the course materials."

        context_parts = ["## Relevant Context from Course Materials\n"]

        # Estimate ~4 characters per token
        char_budget = max_tokens * 4
        current_chars = len(context_parts[0])

        for i, chunk in enumerate(chunks, 1):
            chunk_str = (
                f"\n### Source {i} "
                f"(Score: {chunk.combined_score:.2f})\n"
            )
            chunk_str += chunk.to_context_string()
            chunk_str += "\n"

            # Check if adding this chunk exceeds budget
            if current_chars + len(chunk_str) > char_budget:
                logger.info(
                    f"Reached token budget, included {i-1}/{len(chunks)} chunks"
                )
                break

            context_parts.append(chunk_str)
            current_chars += len(chunk_str)

        return "".join(context_parts)
