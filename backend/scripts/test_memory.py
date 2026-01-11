import asyncio
from uuid import UUID
from app.core.database import AsyncSessionLocal
from app.services.memory_service import MemoryService
from app.repositories.user import UserRepository
from app.repositories.chapter import ChapterRepository

async def test_memory():
    async with AsyncSessionLocal() as session:
        # Get test user
        user_repo = UserRepository(session)
        users = await user_repo.get_all(limit=1)
        if not users:
            print("No users found")
            return
        user = users[0]
        
        # Get a chapter
        chapter_repo = ChapterRepository(session)
        chapters = await chapter_repo.get_all(limit=1)
        if not chapters:
            print("No chapters found")
            return
        chapter = chapters[0]
        
        memory_service = MemoryService(session)
        
        # Test 1: Get relevant history
        print("=" * 50)
        print("TEST 1: Getting relevant history...")
        print(f"Query: 'How do I handle data distribution shift?'")
        
        memories = await memory_service.get_relevant_history(
            user_id=user.id,
            current_chapter_id=chapter.id,
            current_query="How do I handle data distribution shift?",
            max_memories=3
        )
        
        print(f"\nFound {len(memories)} relevant memories:")
        for i, mem in enumerate(memories):
            print(f"\n--- Memory {i+1} ---")
            print(f"Chapter: {mem.chapter_title}")
            print(f"Summary: {mem.summary[:150]}...")
            print(f"Topics: {mem.topics_covered}")
            print(f"Similarity: {mem.similarity_score:.3f}")
        
        # Test 2: Format for prompt
        print("\n" + "=" * 50)
        print("TEST 2: Formatting memories for prompt...")
        
        formatted = await memory_service.format_memories_for_prompt(memories)
        print(f"\nFormatted output:\n{formatted[:500]}...")
        
        # Test 3: Check struggled concepts
        print("\n" + "=" * 50)
        print("TEST 3: Getting struggled concepts history...")
        
        struggled = await memory_service.get_struggled_concepts_history(user.id)
        print(f"Struggled concepts: {struggled}")
        
        print("\n" + "=" * 50)
        print("✅ Memory service test complete!")

if __name__ == "__main__":
    asyncio.run(test_memory())