"""Conversation summary service for analyzing tutoring sessions."""

import json
import logging
import re
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import Conversation
from app.models.conversation_summary import ConversationSummary
from app.models.message import Message
from app.prompts.summary_prompt import (
    build_detailed_summary_prompt,
    build_simple_summary_prompt,
)
from app.repositories.conversation_summary import ConversationSummaryRepository
from app.repositories.chapter import ChapterRepository
from app.repositories.book import BookRepository

logger = logging.getLogger(__name__)


# Pydantic schemas for validation
class ConceptUnderstood(BaseModel):
    """Schema for a concept the student understood."""

    concept: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    evidence: str = ""


class ConceptStruggled(BaseModel):
    """Schema for a concept the student struggled with."""

    concept: str
    severity: str = Field(default="medium")
    evidence: str = ""

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Ensure severity is valid."""
        valid = {"high", "medium", "low"}
        if v.lower() not in valid:
            return "medium"
        return v.lower()


class SummaryAnalysis(BaseModel):
    """Schema for the complete summary analysis from Claude."""

    summary: str = Field(default="Conversation completed.")
    topics_covered: list[str] = Field(default_factory=list)
    concepts_understood: list[ConceptUnderstood | str] = Field(default_factory=list)
    concepts_struggled: list[ConceptStruggled | str] = Field(default_factory=list)
    questions_asked_by_student: int = Field(default=0, alias="questions_asked")
    engagement_level: str = Field(default="medium")
    engagement_score: float = Field(ge=0.0, le=1.0, default=0.5)
    recommended_next_steps: list[str] = Field(default_factory=list)
    prerequisite_gaps: list[str] = Field(default_factory=list)

    class Config:
        populate_by_name = True

    @field_validator("engagement_level")
    @classmethod
    def validate_engagement_level(cls, v: str) -> str:
        """Ensure engagement level is valid."""
        valid = {"high", "medium", "low"}
        if v.lower() not in valid:
            return "medium"
        return v.lower()

    def get_concepts_understood_strings(self) -> list[str]:
        """Extract concept names as strings."""
        result = []
        for item in self.concepts_understood:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, ConceptUnderstood):
                result.append(item.concept)
            elif isinstance(item, dict):
                result.append(item.get("concept", str(item)))
        return result

    def get_concepts_struggled_strings(self) -> list[str]:
        """Extract concept names as strings."""
        result = []
        for item in self.concepts_struggled:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, ConceptStruggled):
                result.append(item.concept)
            elif isinstance(item, dict):
                result.append(item.get("concept", str(item)))
        return result


class SummaryService:
    """Service for generating and storing conversation summaries."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the summary service.

        Args:
            session: Database session
        """
        self.session = session
        self.summary_repo = ConversationSummaryRepository(session)
        self.chapter_repo = ChapterRepository(session)
        self.book_repo = BookRepository(session)
        self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def generate_summary(
        self,
        conversation: Conversation,
        messages: list[Message],
    ) -> ConversationSummary:
        """
        Analyze conversation and generate structured summary.

        Args:
            conversation: The conversation to summarize
            messages: List of messages in the conversation

        Returns:
            ConversationSummary model saved to database

        Raises:
            ValueError: If conversation has no messages
        """
        if not messages:
            raise ValueError("Cannot generate summary for conversation with no messages")

        logger.info(
            f"Generating summary for conversation {conversation.id} "
            f"with {len(messages)} messages"
        )

        # Get chapter context for better analysis
        chapter_context = await self._get_chapter_context(conversation.chapter_id)

        # Convert messages to dict format
        message_dicts = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]

        # Generate analysis using Claude
        analysis = await self._analyze_conversation(message_dicts, chapter_context)

        # Create summary record
        summary = await self._create_summary_record(conversation.id, analysis)

        logger.info(
            f"Generated summary for conversation {conversation.id}: "
            f"{len(analysis.topics_covered)} topics, "
            f"{len(analysis.get_concepts_understood_strings())} understood, "
            f"{len(analysis.get_concepts_struggled_strings())} struggled"
        )

        return summary

    async def _get_chapter_context(self, chapter_id: UUID) -> dict[str, Any]:
        """Get chapter context for summary analysis."""
        try:
            chapter = await self.chapter_repo.get(chapter_id)
            if not chapter:
                return {}

            book = await self.book_repo.get(chapter.book_id)

            return {
                "chapter_id": str(chapter.id),
                "chapter_title": chapter.title,
                "chapter_number": chapter.chapter_number,
                "summary": chapter.summary,
                "key_concepts": chapter.key_concepts or [],
                "book_title": book.title if book else "Unknown Book",
                "book_author": book.author if book else "Unknown Author",
            }
        except Exception as e:
            logger.warning(f"Failed to get chapter context: {e}")
            return {}

    async def _analyze_conversation(
        self,
        messages: list[dict[str, str]],
        chapter_context: dict[str, Any],
    ) -> SummaryAnalysis:
        """
        Use Claude to analyze the conversation.

        Args:
            messages: List of message dicts with 'role' and 'content'
            chapter_context: Chapter information for context

        Returns:
            Validated SummaryAnalysis
        """
        try:
            # Build prompts
            if chapter_context:
                system_prompt, user_prompt = build_detailed_summary_prompt(
                    messages, chapter_context
                )
            else:
                system_prompt = ""
                user_prompt = build_simple_summary_prompt(messages)

            # Call Claude
            response = await self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system=system_prompt if system_prompt else None,
                messages=[{"role": "user", "content": user_prompt}],
            )

            response_text = response.content[0].text

            # Parse and validate JSON
            analysis = self._parse_summary_response(response_text)

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing conversation: {e}", exc_info=True)
            # Return default analysis on error
            return self._create_fallback_analysis(messages)

    def _parse_summary_response(self, response_text: str) -> SummaryAnalysis:
        """
        Parse Claude's response into a validated SummaryAnalysis.

        Handles various response formats:
        - Pure JSON
        - JSON in markdown code blocks
        - JSON with extra text before/after

        Args:
            response_text: Raw response from Claude

        Returns:
            Validated SummaryAnalysis
        """
        # Try to extract JSON from response
        json_str = self._extract_json(response_text)

        if not json_str:
            logger.warning("Could not extract JSON from response, using fallback")
            return SummaryAnalysis()

        try:
            # Parse JSON
            data = json.loads(json_str)

            # Handle case where questions_asked might be under different key
            if "questions_asked_by_student" in data and "questions_asked" not in data:
                data["questions_asked"] = data["questions_asked_by_student"]

            # Validate with Pydantic
            analysis = SummaryAnalysis.model_validate(data)

            return analysis

        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}")
            return SummaryAnalysis()
        except Exception as e:
            logger.warning(f"Validation error: {e}")
            return SummaryAnalysis()

    def _extract_json(self, text: str) -> str | None:
        """
        Extract JSON from text that might contain markdown or extra content.

        Args:
            text: Raw text that might contain JSON

        Returns:
            Extracted JSON string or None
        """
        # Try to find JSON in markdown code blocks
        code_block_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
        matches = re.findall(code_block_pattern, text)
        if matches:
            # Try each match
            for match in matches:
                if match.strip().startswith("{"):
                    return match.strip()

        # Try to find raw JSON object
        # Look for outermost { } pair
        brace_start = text.find("{")
        if brace_start != -1:
            brace_count = 0
            for i, char in enumerate(text[brace_start:], brace_start):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        return text[brace_start : i + 1]

        # No JSON found
        return None

    def _create_fallback_analysis(
        self, messages: list[dict[str, str]]
    ) -> SummaryAnalysis:
        """
        Create a basic fallback analysis when Claude analysis fails.

        Args:
            messages: List of conversation messages

        Returns:
            Basic SummaryAnalysis with estimated values
        """
        # Count student questions
        student_questions = 0
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                student_questions += content.count("?")

        # Estimate engagement based on message count and length
        user_messages = [m for m in messages if m.get("role") == "user"]
        avg_length = (
            sum(len(m.get("content", "")) for m in user_messages) / len(user_messages)
            if user_messages
            else 0
        )

        # Simple engagement heuristic
        if avg_length > 100 and len(user_messages) > 3:
            engagement = 0.8
            engagement_level = "high"
        elif avg_length > 50 or len(user_messages) > 2:
            engagement = 0.6
            engagement_level = "medium"
        else:
            engagement = 0.4
            engagement_level = "low"

        return SummaryAnalysis(
            summary="Conversation completed. Detailed analysis unavailable.",
            topics_covered=[],
            concepts_understood=[],
            concepts_struggled=[],
            questions_asked=student_questions,
            engagement_level=engagement_level,
            engagement_score=engagement,
            recommended_next_steps=[],
            prerequisite_gaps=[],
        )

    async def _create_summary_record(
        self,
        conversation_id: UUID,
        analysis: SummaryAnalysis,
    ) -> ConversationSummary:
        """
        Create and save the ConversationSummary record.

        Args:
            conversation_id: ID of the conversation
            analysis: Validated analysis from Claude

        Returns:
            Saved ConversationSummary model
        """
        summary_data = {
            "id": uuid4(),
            "conversation_id": conversation_id,
            "summary": analysis.summary,
            "topics_covered": analysis.topics_covered,
            "concepts_understood": analysis.get_concepts_understood_strings(),
            "concepts_struggled": analysis.get_concepts_struggled_strings(),
            "questions_asked": analysis.questions_asked_by_student,
            "engagement_score": analysis.engagement_score,
            "created_at": datetime.utcnow(),
        }

        summary = await self.summary_repo.create(summary_data)
        await self.session.commit()

        return summary

    async def get_summary(self, conversation_id: UUID) -> ConversationSummary | None:
        """
        Get existing summary for a conversation.

        Args:
            conversation_id: ID of the conversation

        Returns:
            ConversationSummary if exists, None otherwise
        """
        return await self.summary_repo.get_by_conversation_id(conversation_id)

    async def get_user_summaries(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> list[ConversationSummary]:
        """
        Get recent summaries for a user's conversations.

        Args:
            user_id: User ID
            limit: Maximum number of summaries to return

        Returns:
            List of ConversationSummary models
        """
        return await self.summary_repo.get_by_user(user_id, limit=limit)
