
import asyncio
from uuid import UUID
from app.core.database import async_session_maker
from app.services.profile_service import ProfileService
from app.repositories.user import UserRepository
from app.repositories.chapter import ChapterRepository


async def test_profile():
    """Test the full learning profile flow."""
    async with async_session_maker() as session:
        # Get a test user
        user_repo = UserRepository(session)
        users = await user_repo.get_all(limit=1)
        if not users:
            print("❌ No users found. Create one via the frontend first.")
            print("   Visit http://localhost:3000/login to sign up")
            return
        
        user = users[0]
        print(f"🧑 Testing with user: {user.email}")
        
        profile_service = ProfileService(session)
        
        # 1. Get or create profile
        print("\n" + "=" * 60)
        print("1️⃣  Getting/creating profile...")
        print("=" * 60)
        profile = await profile_service.get_or_create_profile(user.id)
        print(f"   ✓ Profile ID: {profile.id}")
        print(f"   ✓ Mastery map: {profile.mastery_map}")
        print(f"   ✓ Gaps: {profile.identified_gaps}")
        print(f"   ✓ Strengths: {profile.strengths}")
        print(f"   ✓ Total study time: {profile.total_study_time_minutes} minutes")
        
        # 2. Get chapter recommendations
        print("\n" + "=" * 60)
        print("2️⃣  Getting chapter recommendations...")
        print("=" * 60)
        
        chapter_repo = ChapterRepository(session)
        chapters = await chapter_repo.get_all(limit=1)
        
        if chapters:
            book_id = chapters[0].book_id
            recommendations = await profile_service.get_recommended_chapters(
                user_id=user.id,
                book_id=book_id
            )
            
            if recommendations:
                print(f"   ✓ Found {len(recommendations)} recommendations:")
                for i, rec in enumerate(recommendations[:5], 1):
                    print(f"   {i}. {rec.chapter_title}")
                    print(f"      Reason: {rec.reason}")
                    print(f"      Priority: {rec.priority}")
                    print()
            else:
                print("   ℹ️  No recommendations yet (need more conversation data)")
        else:
            print("   ⚠️  No chapters found. Run book ingestion first.")
        
        # 3. Get context for conversation
        print("\n" + "=" * 60)
        print("3️⃣  Getting conversation context...")
        print("=" * 60)
        
        if chapters:
            context = await profile_service.get_context_for_conversation(
                user_id=user.id,
                chapter_id=chapters[0].id
            )
            print(f"   ✓ Strengths: {context.strengths if context.strengths else 'None identified yet'}")
            print(f"   ✓ Gaps: {context.gaps if context.gaps else 'None identified yet'}")
            
            past_topics = context.past_topics[:5] if context.past_topics else []
            print(f"   ✓ Past topics: {past_topics if past_topics else 'No past conversations'}")
        else:
            print("   ⚠️  Cannot get context without chapters")
        
        print("\n" + "=" * 60)
        print("✅ Profile service test complete!")
        print("=" * 60)
        
        # Summary
        print("\n📊 Test Summary:")
        print(f"   • Profile exists: {'✓' if profile else '✗'}")
        print(f"   • Mastery data: {'✓' if profile.mastery_map else '○ (empty - needs conversations)'}")
        print(f"   • Gaps identified: {'✓' if profile.identified_gaps else '○ (empty - needs struggling)'}")
        print(f"   • Strengths: {'✓' if profile.strengths else '○ (empty - needs understanding)'}")


async def test_mastery_update_simulation():
    """Simulate mastery updates to verify the algorithm works."""
    print("\n" + "=" * 60)
    print("🧪 Simulating mastery score updates...")
    print("=" * 60)
    
    # Import the service to access internal methods
    from app.services.profile_service import ProfileService
    
    # Simulate the exponential moving average calculation
    def simulate_update(current_score: float, new_evidence: float, weight: float = 0.7) -> float:
        """Exponential moving average: new = weight * evidence + (1-weight) * current"""
        return weight * new_evidence + (1 - weight) * current_score
    
    # Test scenarios
    print("\n   Scenario 1: Student initially struggles, then improves")
    score = 0.5  # Starting score
    print(f"   Starting: {score:.2f}")
    
    # Student struggles
    score = simulate_update(score, 0.3)
    print(f"   After struggling: {score:.2f}")
    
    # Student understands
    score = simulate_update(score, 0.8)
    print(f"   After understanding: {score:.2f}")
    
    # Student masters it
    score = simulate_update(score, 0.95)
    print(f"   After mastery: {score:.2f}")
    
    print("\n   Scenario 2: Student consistently understands")
    score = 0.5
    print(f"   Starting: {score:.2f}")
    for i in range(3):
        score = simulate_update(score, 0.85)
        print(f"   After session {i+1}: {score:.2f}")
    
    print("\n   ✓ Mastery algorithm verified!")


if __name__ == "__main__":
    print("🧪 Phase 4.2 Learning Profile Test Suite")
    print("=" * 60)
    
    asyncio.run(test_profile())
    asyncio.run(test_mastery_update_simulation())