import asyncio
from uuid import UUID
from app.services.rag_service import RAGService
from app.core.database import AsyncSessionLocal

async def test_rag():
    # Get a database session using the session factory directly
    async with AsyncSessionLocal() as session:
        rag_service = RAGService(session)
        
        # Test 1: Basic retrieval (no chapter filter)
        print("=" * 50)
        print("TEST 1: Basic retrieval - 'What is feature engineering?'")
        print("=" * 50)
        
        results = await rag_service.retrieve(
            query="What is feature engineering?",
            top_k=3
        )
        
        for i, chunk in enumerate(results):
            print(f"\n--- Result {i+1} (score: {chunk.score:.3f}) ---")
            print(f"Chapter: {chunk.section_title or 'N/A'}")
            print(f"Content preview: {chunk.content[:200]}...")
        
        # Test 2: Retrieval with chapter filter
        from sqlalchemy import select
        from app.models.chapter import Chapter
        
        chapter_result = await session.execute(select(Chapter).limit(1))
        chapter = chapter_result.scalar_one_or_none()
        
        if chapter:
            print("\n" + "=" * 50)
            print(f"TEST 2: Chapter-filtered retrieval - Chapter: {chapter.title}")
            print("=" * 50)
            
            results = await rag_service.retrieve(
                query="machine learning",
                chapter_id=chapter.id,
                top_k=3
            )
            
            for i, chunk in enumerate(results):
                print(f"\n--- Result {i+1} (score: {chunk.score:.3f}) ---")
                print(f"Content preview: {chunk.content[:200]}...")
        
        # Test 3: Test retrieve_with_context
        print("\n" + "=" * 50)
        print("TEST 3: Retrieve with conversation context")
        print("=" * 50)
        
        if chapter:
            from app.schemas.message import MessageInDB
            from datetime import datetime
            
            mock_history = [
                MessageInDB(
                    id=UUID('00000000-0000-0000-0000-000000000001'),
                    conversation_id=UUID('00000000-0000-0000-0000-000000000000'),
                    role="user",
                    content="I want to learn about model deployment",
                    created_at=datetime.now()
                ),
                MessageInDB(
                    id=UUID('00000000-0000-0000-0000-000000000002'),
                    conversation_id=UUID('00000000-0000-0000-0000-000000000000'),
                    role="assistant", 
                    content="Great! Model deployment involves moving your trained model to production.",
                    created_at=datetime.now()
                )
            ]
            
            context = await rag_service.retrieve_with_context(
                query="How do I monitor model performance?",
                chapter_id=chapter.id,
                conversation_history=mock_history,
                top_k=3
            )
            
            print(f"Chapter: {context.chapter_title}")
            print(f"Retrieved {len(context.chunks)} chunks")
            print(f"\nFormatted context preview:\n{context.formatted_content[:500]}...")
        
        print("\n" + "=" * 50)
        print("✅ RAG Service tests completed!")
        print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_rag())