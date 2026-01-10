"""Chat service for Socratic dialogue with students."""

import logging
from datetime import datetime
from typing import Any, AsyncGenerator
from uuid import UUID, uuid4

from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import Conversation, ConversationStatus
from app.models.conversation_summary import ConversationSummary
from app.models.message import Message
from app.repositories.chapter import ChapterRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.learning_profile import LearningProfileRepository
from app.repositories.message import MessageRepository
from app.services.rag_service import RAGService
from app.services.summary_service import SummaryService
from app.services.profile_service import ProfileService
from app.prompts.socratic_tutor import (
    build_socratic_prompt,
    build_initial_greeting_prompt,
)

logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing Socratic tutoring conversations with streaming support."""

    # Context length management
    MAX_MESSAGES_IN_CONTEXT = 20  # Keep last 20 messages for context
    MAX_TOKENS_PER_MESSAGE = 4000  # For RAG context

    def __init__(self, session: AsyncSession):
        """
        Initialize chat service.

        Args:
            session: Database session
        """
        self.session = session
        self.rag_service = RAGService(session)
        self.conversation_repo = ConversationRepository(session)
        self.message_repo = MessageRepository(session)
        self.summary_service = SummaryService(session)
        self.profile_service = ProfileService(session)
        self.profile_repo = LearningProfileRepository(session)
        self.chapter_repo = ChapterRepository(session)
        self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def create_conversation(
        self, user_id: UUID, chapter_id: UUID
    ) -> Conversation:
        """
        Start a new conversation for a chapter.

        Args:
            user_id: User UUID
            chapter_id: Chapter UUID

        Returns:
            Created Conversation model

        Raises:
            ValueError: If chapter not found
        """
        logger.info(f"Creating conversation: user={user_id}, chapter={chapter_id}")

        # Verify chapter exists by getting its context
        chapter_context = await self.rag_service.get_chapter_context(chapter_id)

        # Create conversation record
        conversation_id = uuid4()
        conversation_data = {
            "id": conversation_id,
            "user_id": user_id,
            "chapter_id": chapter_id,
            "started_at": datetime.utcnow(),
            "status": ConversationStatus.ACTIVE,
        }

        conversation = await self.conversation_repo.create(conversation_data)
        await self.session.commit()

        # Generate and save initial greeting
        greeting = await self._generate_initial_greeting(chapter_context)

        await self.message_repo.create(
            {
                "id": uuid4(),
                "conversation_id": conversation_id,
                "role": "assistant",
                "content": greeting,
                "created_at": datetime.utcnow(),
            }
        )
        await self.session.commit()

        logger.info(f"Conversation created: {conversation_id}")
        return conversation

    async def send_message(
        self, conversation_id: UUID, user_message: str
    ) -> AsyncGenerator[str, None]:
        """
        Process user message and stream AI response.

        Uses RAG to get relevant content and Socratic prompting strategy.

        Args:
            conversation_id: Conversation UUID
            user_message: User's message content

        Yields:
            Chunks of the AI response as they're generated

        Raises:
            ValueError: If conversation not found or not active
        """
        logger.info(f"Processing message for conversation {conversation_id}")

        # 1. Verify conversation exists and is active
        conversation = await self.conversation_repo.get(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        if conversation.status != ConversationStatus.ACTIVE:
            raise ValueError(
                f"Conversation is {conversation.status}, not active. "
                "Please start a new conversation."
            )

        # 2. Save user message to database
        user_message_id = uuid4()
        await self.message_repo.create(
            {
                "id": user_message_id,
                "conversation_id": conversation_id,
                "role": "user",
                "content": user_message,
                "created_at": datetime.utcnow(),
            }
        )
        await self.session.commit()

        # 3. Retrieve relevant chunks via RAG
        logger.debug("Retrieving relevant content via RAG")
        rag_context = await self.rag_service.retrieve_with_context(
            query=user_message,
            chapter_id=conversation.chapter_id,
            conversation_history=await self._get_recent_messages(conversation_id),
            top_k=5,
        )

        # 4. Get user's learning profile
        learning_profile = await self._get_learning_profile(conversation.user_id)

        # 5. Build complete prompt with all context
        formatted_context = await self.rag_service.format_context_for_llm(
            rag_context.chunks, max_tokens=self.MAX_TOKENS_PER_MESSAGE
        )

        system_prompt = build_socratic_prompt(
            chapter_context=rag_context.chapter_info,
            retrieved_content=formatted_context,
            learning_profile=learning_profile,
            conversation_summary=None,  # TODO: Add mid-conversation summaries
        )

        # 6. Get conversation history for Claude
        messages = await self._build_claude_messages(conversation_id)

        # 7. Stream response from Claude API
        logger.debug("Streaming response from Claude API")
        full_response = ""

        try:
            async with self.anthropic_client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system=system_prompt,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    full_response += text
                    yield text

        except Exception as e:
            logger.error(f"Error streaming from Claude: {e}", exc_info=True)
            error_message = "I apologize, but I encountered an error. Please try again."
            yield error_message
            full_response = error_message

        # 8. Save assistant message to database
        await self.message_repo.create(
            {
                "id": uuid4(),
                "conversation_id": conversation_id,
                "role": "assistant",
                "content": full_response,
                "created_at": datetime.utcnow(),
            }
        )
        await self.session.commit()

        logger.info(f"Message processed successfully for conversation {conversation_id}")

    async def end_conversation(
        self, conversation_id: UUID
    ) -> ConversationSummary:
        """
        End conversation and generate summary.

        Triggers learning profile update.

        Args:
            conversation_id: Conversation UUID

        Returns:
            Generated ConversationSummary

        Raises:
            ValueError: If conversation not found
        """
        logger.info(f"Ending conversation {conversation_id}")

        # Verify conversation exists
        conversation = await self.conversation_repo.get(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Update conversation status
        await self.conversation_repo.update(
            conversation_id,
            {
                "status": ConversationStatus.COMPLETED,
                "ended_at": datetime.utcnow(),
            },
        )
        await self.session.commit()

        # Get messages for summary
        messages = await self.message_repo.get_by_conversation(conversation_id)

        # Generate conversation summary using SummaryService
        summary = await self.summary_service.generate_summary(
            conversation=conversation,
            messages=messages,
        )

        # Trigger learning profile update based on summary
        try:
            chapter = await self.chapter_repo.get(conversation.chapter_id)
            if chapter:
                await self.profile_service.update_from_summary(
                    user_id=conversation.user_id,
                    summary=summary,
                    chapter=chapter,
                )
                logger.info(f"Learning profile updated for user {conversation.user_id}")
            else:
                logger.warning(f"Chapter {conversation.chapter_id} not found, skipping profile update")
        except Exception as e:
            # Don't fail the entire end_conversation if profile update fails
            logger.error(f"Failed to update learning profile: {e}", exc_info=True)

        logger.info(f"Conversation {conversation_id} ended successfully")
        return summary

    async def get_conversation_with_messages(
        self, conversation_id: UUID
    ) -> dict[str, Any]:
        """
        Get conversation with all messages.

        Args:
            conversation_id: Conversation UUID

        Returns:
            Dictionary with conversation and messages

        Raises:
            ValueError: If conversation not found
        """
        conversation = await self.conversation_repo.get(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        messages = await self.message_repo.get_by_conversation(conversation_id)

        return {
            "conversation": {
                "id": str(conversation.id),
                "user_id": str(conversation.user_id),
                "chapter_id": str(conversation.chapter_id),
                "started_at": conversation.started_at.isoformat(),
                "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
                "status": conversation.status.value,
            },
            "messages": [
                {
                    "id": str(msg.id),
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in messages
            ],
        }

    async def list_user_conversations(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> list[dict[str, Any]]:
        """
        List conversations for a user.

        Args:
            user_id: User UUID
            limit: Maximum number to return
            offset: Offset for pagination

        Returns:
            List of conversation summaries
        """
        conversations = await self.conversation_repo.get_by_user(
            user_id, limit=limit, offset=offset
        )

        return [
            {
                "id": str(conv.id),
                "chapter_id": str(conv.chapter_id),
                "started_at": conv.started_at.isoformat(),
                "ended_at": conv.ended_at.isoformat() if conv.ended_at else None,
                "status": conv.status.value,
            }
            for conv in conversations
        ]

    # Private helper methods

    async def _generate_initial_greeting(self, chapter_context: dict[str, Any]) -> str:
        """Generate personalized initial greeting."""
        prompt = build_initial_greeting_prompt(chapter_context)

        response = await self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    async def _get_recent_messages(
        self, conversation_id: UUID
    ) -> list[Message]:
        """Get recent messages for context, respecting limits."""
        all_messages = await self.message_repo.get_by_conversation(conversation_id)

        # Return last N messages
        return all_messages[-self.MAX_MESSAGES_IN_CONTEXT:]

    async def _build_claude_messages(
        self, conversation_id: UUID
    ) -> list[dict[str, str]]:
        """Build message history for Claude API."""
        messages = await self._get_recent_messages(conversation_id)

        # Filter out system messages and format for Claude
        claude_messages = []
        for msg in messages:
            if msg.role in ("user", "assistant"):
                claude_messages.append(
                    {"role": msg.role, "content": msg.content}
                )

        return claude_messages

    async def _get_learning_profile(self, user_id: UUID) -> dict[str, Any] | None:
        """Get user's learning profile."""
        try:
            profile = await self.profile_repo.get_by_user(user_id)
            if not profile:
                return None

            return {
                "strengths": profile.strengths or [],
                "identified_gaps": profile.identified_gaps or [],
                "mastery_map": profile.mastery_map or {},
            }
        except Exception as e:
            logger.warning(f"Could not load learning profile: {e}")
            return None
