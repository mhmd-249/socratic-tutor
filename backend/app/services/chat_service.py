"""Chat service for Socratic dialogue with students."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import ConversationStatus
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)


class ChatMessage:
    """Represents a chat message."""

    def __init__(self, role: str, content: str):
        """
        Initialize chat message.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        self.role = role
        self.content = content

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        return {"role": self.role, "content": self.content}


class ChatService:
    """Service for managing Socratic tutoring conversations."""

    SOCRATIC_SYSTEM_PROMPT = """You are an expert AI tutor using the Socratic method to help students learn. Your teaching philosophy:

1. **Never give direct answers immediately** - Guide students to discover answers themselves
2. **Ask probing questions** - Assess their current understanding before explaining
3. **Build on existing knowledge** - Connect new concepts to what they already know
4. **Provide hints, not solutions** - Give progressively clearer hints if they struggle
5. **Use analogies and examples** - Make abstract concepts concrete
6. **Check understanding** - Don't move forward until they grasp the current concept
7. **Be encouraging** - Celebrate insights and effort, not just correct answers
8. **Stay on topic** - Keep the conversation focused on the chapter's concepts

You have access to relevant excerpts from the course textbook. Use these to:
- Verify the accuracy of your explanations
- Reference specific examples or definitions from the book
- Guide students to key passages

Remember: Your goal is to help them **think**, not just to give them answers."""

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
        self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def start_conversation(
        self, user_id: UUID, chapter_id: UUID
    ) -> dict[str, Any]:
        """
        Start a new conversation for a chapter.

        Args:
            user_id: User UUID
            chapter_id: Chapter UUID

        Returns:
            Conversation data with initial greeting
        """
        logger.info(f"Starting conversation for user {user_id}, chapter {chapter_id}")

        # Get chapter context
        chapter_context = await self.rag_service.get_chapter_context(chapter_id)

        # Create conversation record
        conversation_id = uuid4()
        conversation = await self.conversation_repo.create(
            {
                "id": conversation_id,
                "user_id": user_id,
                "chapter_id": chapter_id,
                "started_at": datetime.utcnow(),
                "status": ConversationStatus.ACTIVE,
            }
        )
        await self.session.commit()

        # Create system message with chapter context
        system_content = self._create_chapter_system_message(chapter_context)
        await self.message_repo.create(
            {
                "id": uuid4(),
                "conversation_id": conversation_id,
                "role": "system",
                "content": system_content,
                "created_at": datetime.utcnow(),
            }
        )

        # Generate initial greeting
        greeting = await self._generate_initial_greeting(chapter_context)

        # Save assistant greeting
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

        logger.info(f"Conversation {conversation_id} started successfully")

        return {
            "conversation_id": str(conversation_id),
            "chapter": chapter_context,
            "message": greeting,
        }

    async def send_message(
        self, conversation_id: UUID, user_message: str
    ) -> dict[str, Any]:
        """
        Send a user message and get AI response.

        Args:
            conversation_id: Conversation UUID
            user_message: User's message content

        Returns:
            Assistant's response with metadata
        """
        logger.info(f"Processing message for conversation {conversation_id}")

        # Verify conversation exists and is active
        conversation = await self.conversation_repo.get(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        if conversation.status != ConversationStatus.ACTIVE:
            raise ValueError(f"Conversation is {conversation.status}, not active")

        # Save user message
        await self.message_repo.create(
            {
                "id": uuid4(),
                "conversation_id": conversation_id,
                "role": "user",
                "content": user_message,
                "created_at": datetime.utcnow(),
            }
        )
        await self.session.commit()

        # Retrieve relevant context using RAG
        retrieved_chunks = await self.rag_service.retrieve_context(
            query=user_message,
            chapter_id=conversation.chapter_id,
            limit=5,
            min_similarity=0.5,
        )

        # Format context
        rag_context = await self.rag_service.format_context_for_llm(
            retrieved_chunks, max_tokens=4000
        )

        # Get conversation history
        messages = await self.message_repo.get_by_conversation(conversation_id)

        # Build Claude messages (exclude system messages, handle them separately)
        claude_messages = []
        system_message = None

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                claude_messages.append(
                    {"role": msg.role, "content": msg.content}
                )

        # Add RAG context to the user's latest message
        enhanced_user_message = f"{user_message}\n\n{rag_context}"
        claude_messages[-1]["content"] = enhanced_user_message

        # Generate response from Claude
        response = await self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=f"{self.SOCRATIC_SYSTEM_PROMPT}\n\n{system_message}",
            messages=claude_messages,
        )

        assistant_message = response.content[0].text

        # Save assistant response
        await self.message_repo.create(
            {
                "id": uuid4(),
                "conversation_id": conversation_id,
                "role": "assistant",
                "content": assistant_message,
                "created_at": datetime.utcnow(),
            }
        )
        await self.session.commit()

        logger.info(f"Response generated for conversation {conversation_id}")

        return {
            "message": assistant_message,
            "sources": [chunk.to_dict() for chunk in retrieved_chunks],
        }

    async def end_conversation(self, conversation_id: UUID) -> dict[str, Any]:
        """
        End a conversation and mark it as completed.

        Args:
            conversation_id: Conversation UUID

        Returns:
            Conversation summary data
        """
        logger.info(f"Ending conversation {conversation_id}")

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

        logger.info(f"Conversation {conversation_id} ended successfully")

        return {
            "conversation_id": str(conversation_id),
            "status": "completed",
            "message": "Conversation ended. Great work!",
        }

    async def get_conversation_history(
        self, conversation_id: UUID
    ) -> list[dict[str, Any]]:
        """
        Get full conversation history.

        Args:
            conversation_id: Conversation UUID

        Returns:
            List of messages
        """
        messages = await self.message_repo.get_by_conversation(conversation_id)

        # Filter out system messages from user-facing history
        return [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
            if msg.role != "system"
        ]

    def _create_chapter_system_message(self, chapter_context: dict[str, Any]) -> str:
        """
        Create system message with chapter context.

        Args:
            chapter_context: Chapter metadata

        Returns:
            Formatted system message
        """
        key_concepts = ", ".join(chapter_context.get("key_concepts", []))

        return f"""## Chapter Context

**Book**: {chapter_context['book_title']} by {chapter_context['book_author']}
**Chapter {chapter_context['chapter_number']}**: {chapter_context['chapter_title']}

**Summary**: {chapter_context['summary']}

**Key Concepts**: {key_concepts if key_concepts else 'Not specified'}

Your role is to help the student understand this chapter using the Socratic method."""

    async def _generate_initial_greeting(
        self, chapter_context: dict[str, Any]
    ) -> str:
        """
        Generate personalized initial greeting for the chapter.

        Args:
            chapter_context: Chapter metadata

        Returns:
            Greeting message
        """
        system_prompt = f"""{self.SOCRATIC_SYSTEM_PROMPT}

{self._create_chapter_system_message(chapter_context)}"""

        response = await self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": "Generate a brief, friendly greeting to start our study session. Ask an opening question to assess my current familiarity with this chapter's topic. Keep it warm and encouraging.",
                }
            ],
        )

        return response.content[0].text
