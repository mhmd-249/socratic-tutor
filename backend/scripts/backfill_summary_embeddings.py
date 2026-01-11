import asyncio
from app.core.database import AsyncSessionLocal
from app.services.embedding_service import EmbeddingService
from app.repositories.conversation_summary import ConversationSummaryRepository
from sqlalchemy import select, update
from app.models.conversation_summary import ConversationSummary

async def backfill():
    async with AsyncSessionLocal() as session:
        embedding_service = EmbeddingService()
        
        # Get summaries without embeddings
        result = await session.execute(
            select(ConversationSummary).where(ConversationSummary.embedding == None)
        )
        summaries = result.scalars().all()
        
        print(f"Found {len(summaries)} summaries without embeddings")
        
        for summary in summaries:
            # Create text for embedding
            text_parts = [summary.summary or ""]
            if summary.topics_covered:
                text_parts.append(f"Topics: {', '.join(summary.topics_covered)}")
            
            combined_text = " ".join(text_parts)
            
            if combined_text.strip():
                embedding = await embedding_service.generate_embedding(combined_text)
                summary.embedding = embedding
                print(f"  Generated embedding for summary {summary.id}")
        
        await session.commit()
        print("✅ Backfill complete!")

if __name__ == "__main__":
    asyncio.run(backfill())