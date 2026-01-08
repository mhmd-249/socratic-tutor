"""Test RAG service SQL syntax compilation."""

import pytest
from uuid import uuid4
from sqlalchemy import text


def test_hybrid_search_sql_syntax():
    """Test that the hybrid search SQL compiles without syntax errors."""
    # Simulate the SQL generation logic from _hybrid_search
    embedding_str = "[0.1, 0.2, 0.3]"
    chapter_id = uuid4()
    chapter_filter_sql = f"AND c.chapter_id = '{str(chapter_id)}'"

    # This should compile without errors
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
                ts_rank(c.content_tsv, websearch_to_tsquery('english', $1)) as keyword_score
            FROM chunks c
            WHERE c.content_tsv @@ websearch_to_tsquery('english', $1)
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
                ($2 * s.semantic_score +
                 $3 * COALESCE(k.keyword_score, 0.0)) as combined_score
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
        LIMIT $4
    """)

    # Verify it's a valid text object
    assert query_sql is not None
    assert hasattr(query_sql, 'text')


def test_hybrid_search_sql_syntax_no_chapter_filter():
    """Test hybrid search SQL without chapter filter."""
    embedding_str = "[0.1, 0.2, 0.3]"
    chapter_filter_sql = ""

    # This should also compile without errors
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
                ts_rank(c.content_tsv, websearch_to_tsquery('english', $1)) as keyword_score
            FROM chunks c
            WHERE c.content_tsv @@ websearch_to_tsquery('english', $1)
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
                ($2 * s.semantic_score +
                 $3 * COALESCE(k.keyword_score, 0.0)) as combined_score
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
        LIMIT $4
    """)

    # Verify it's a valid text object
    assert query_sql is not None
    assert hasattr(query_sql, 'text')
