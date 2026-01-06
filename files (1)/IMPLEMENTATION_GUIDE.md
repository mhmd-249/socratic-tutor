# Claude Code Implementation Guide
## AI Socratic Tutor - Step by Step

This guide contains the exact prompts to use with Claude Code at each phase.
Copy each prompt when you're ready for that phase.

---

## PHASE 0: Project Setup (Run Once)

### Prompt 0.1: Initialize Project Structure

```
Initialize a new full-stack project called "socratic-tutor" with the following structure:

1. Create a Next.js 14 frontend with:
   - TypeScript strict mode
   - Tailwind CSS
   - App router
   - src/ directory structure
   - ESLint + Prettier configured

2. Create a FastAPI backend with:
   - Python 3.12
   - Poetry for dependency management
   - The folder structure from CLAUDE.md
   - Alembic for migrations
   - pytest configured

3. Create docker-compose.yml with:
   - PostgreSQL 16 with pgvector extension
   - Backend service
   - Frontend service (for local dev)

4. Create .env.example files for both frontend and backend

5. Create a Makefile with common commands:
   - make dev (start all services)
   - make backend (start backend only)
   - make frontend (start frontend only)
   - make migrate (run migrations)
   - make test (run all tests)

Do NOT implement any features yet - just the scaffolding and configuration.
Ensure all configs follow the standards in CLAUDE.md.
```

### Prompt 0.2: Database Setup

```
Set up the database layer:

1. Create all SQLAlchemy models as defined in CLAUDE.md:
   - users, books, chapters, chunks, conversations, messages, conversation_summaries, learning_profiles
   - Use UUID for all primary keys
   - Include proper relationships and indexes
   - Add pgvector column type for embeddings

2. Create the initial Alembic migration

3. Create Pydantic schemas for each model:
   - Create schemas (for creation)
   - Update schemas (for updates)
   - Response schemas (for API responses)
   - Put in backend/app/schemas/

4. Create repository classes with basic CRUD operations:
   - BaseRepository with common operations
   - Specific repositories inheriting from base
   - All methods should be async
   - Put in backend/app/repositories/

5. Create a database session manager in core/database.py

Run the migration against the local PostgreSQL to verify it works.
```

---

## PHASE 1: Authentication

### Prompt 1.1: Supabase Auth Integration

```
Implement Supabase authentication:

BACKEND:
1. Create auth dependencies in core/security.py:
   - get_current_user: Validate Supabase JWT, return user
   - require_auth: Dependency that raises 401 if not authenticated

2. Create auth endpoints in api/v1/endpoints/auth.py:
   - POST /auth/callback: Handle Supabase auth callback, create/update user in our DB
   - GET /auth/me: Return current user profile

3. Add middleware to extract and validate JWT from Authorization header

FRONTEND:
1. Set up Supabase client in lib/supabase.ts

2. Create AuthProvider context:
   - Handle sign in, sign out, sign up
   - Store session state
   - Auto-refresh tokens

3. Create auth pages:
   - /login: Email/password login with Supabase UI
   - /signup: Registration page
   - Redirect to /dashboard after auth

4. Create a ProtectedRoute component that redirects to /login if not authenticated

5. Create useAuth hook for accessing auth state

Test the full flow: signup -> login -> access protected route -> logout
```

---

## PHASE 2: Book Ingestion & RAG Setup

### Prompt 2.1: PDF Processing Pipeline

```
Create the book ingestion pipeline:

1. Create a script at scripts/ingest_book.py that:
   - Takes a PDF file path and book metadata as arguments
   - Extracts text from PDF (use PyMuPDF/fitz)
   - Detects chapter boundaries (look for "Chapter X" patterns or provide manual markers)
   - Creates Book and Chapter records in database

2. Create the chunking service at services/chunking_service.py:
   - Implement paragraph-based chunking with these parameters:
     - target_chunk_size: 600 tokens
     - max_chunk_size: 800 tokens  
     - overlap: 100 tokens
   - Preserve section headers in metadata
   - Track source page numbers
   - Return chunks with metadata

3. Create the embedding service at services/embedding_service.py:
   - Use OpenAI text-embedding-3-small (or make it configurable)
   - Batch embeddings for efficiency (max 100 per request)
   - Handle rate limiting with exponential backoff
   - Store embeddings in chunks table

4. Update the ingestion script to:
   - Chunk each chapter
   - Generate embeddings
   - Store chunks with embeddings in database

5. Create a simple CLI interface:
   python -m scripts.ingest_book --pdf path/to/book.pdf --title "Book Title" --author "Author"

Make the chunking strategy configurable so we can experiment later.
Include progress logging throughout the process.
```

### Prompt 2.2: RAG Retrieval Service

```
Implement the RAG retrieval service:

1. Create services/rag_service.py with:

   class RAGService:
       async def retrieve(
           self,
           query: str,
           chapter_id: UUID | None = None,
           top_k: int = 5,
           similarity_threshold: float = 0.7
       ) -> list[RetrievedChunk]:
           """
           Retrieve relevant chunks using hybrid search.
           If chapter_id provided, limit search to that chapter.
           """

       async def retrieve_with_context(
           self,
           query: str,
           chapter_id: UUID,
           conversation_history: list[Message],
           top_k: int = 5
       ) -> RAGContext:
           """
           Retrieve chunks considering conversation context.
           Returns chunks + chapter info + relevant prerequisites.
           """

2. Implement hybrid search:
   - Semantic search using pgvector (cosine similarity)
   - Keyword search using PostgreSQL full-text search
   - Combine scores with configurable weights (default: 0.7 semantic, 0.3 keyword)

3. Create the pgvector index:
   - Add migration for HNSW index on chunks.embedding
   - Configure for cosine distance

4. Add a reranking step (optional but recommended):
   - Score chunks by relevance to query + conversation context
   - Can use a simple heuristic or call Claude for reranking

5. Create tests:
   - Test retrieval returns relevant chunks
   - Test chapter filtering works
   - Test empty results handled gracefully

Include detailed logging for debugging retrieval quality.
```

---

## PHASE 3: Chat & Socratic Dialogue

### Prompt 3.1: Chat Service Core

```
Implement the core chat service:

1. Create services/chat_service.py:

   class ChatService:
       async def create_conversation(
           self,
           user_id: UUID,
           chapter_id: UUID
       ) -> Conversation:
           """Start a new conversation for a chapter."""

       async def send_message(
           self,
           conversation_id: UUID,
           user_message: str
       ) -> AsyncGenerator[str, None]:
           """
           Process user message and stream AI response.
           Uses RAG to get relevant content.
           Uses Socratic prompting strategy.
           """

       async def end_conversation(
           self,
           conversation_id: UUID
       ) -> ConversationSummary:
           """
           End conversation and generate summary.
           Triggers learning profile update.
           """

2. Create the Socratic system prompt in prompts/socratic_tutor.py:
   - Define the tutor's personality and approach
   - Include instructions for Socratic method
   - Add placeholders for: chapter_context, retrieved_content, learning_profile, conversation_history

3. Implement the message flow:
   a. Save user message to database
   b. Retrieve relevant chunks via RAG
   c. Get user's learning profile
   d. Build prompt with all context
   e. Stream response from Claude API
   f. Save assistant message to database
   g. Return streaming response

4. Create API endpoints in api/v1/endpoints/chat.py:
   - POST /conversations: Start new conversation
   - POST /conversations/{id}/messages: Send message (streaming response)
   - POST /conversations/{id}/end: End conversation
   - GET /conversations/{id}: Get conversation with messages
   - GET /conversations: List user's conversations

5. Handle edge cases:
   - Conversation already ended
   - Rate limiting
   - Context length limits (truncate old messages if needed)

Use Server-Sent Events (SSE) for streaming responses.
```

### Prompt 3.2: Socratic Prompt Engineering

```
Create and refine the Socratic tutor prompts:

1. Create prompts/socratic_tutor.py with the main system prompt:

SOCRATIC_SYSTEM_PROMPT = '''
You are an expert AI tutor specializing in teaching AI/ML concepts through the Socratic method.

## Your Teaching Philosophy
- Never give direct answers immediately
- Guide students to discover understanding through questions
- Build on what the student already knows
- Use analogies and real-world examples
- Celebrate progress and correct misconceptions gently

## Your Approach
1. When a student asks a question:
   - First, ask what they already know about the topic
   - Identify any misconceptions
   - Ask probing questions to guide their thinking

2. When explaining concepts:
   - Start with the intuition before the math
   - Use concrete examples before abstract definitions
   - Check understanding before moving on: "Does this make sense? Can you explain it back to me?"

3. When a student is struggling:
   - Break down into smaller pieces
   - Provide hints, not answers
   - Reference simpler concepts they should understand first
   - If they need prerequisites, suggest: "I think we should review [concept] from [chapter] first. Would you like to do that?"

## Chapter Context
You are teaching from: {chapter_title}
Chapter summary: {chapter_summary}
Key concepts in this chapter: {key_concepts}

## Relevant Content from the Book
{retrieved_content}

## Student's Learning Profile
Strengths: {strengths}
Areas needing work: {gaps}
Previous topics studied: {topics_studied}

## Conversation Guidelines
- Keep responses focused and not too long
- Ask ONE question at a time
- Use markdown for formatting when helpful
- If the student seems lost, offer to explain prerequisites
'''

2. Create helper functions:
   - format_retrieved_content(chunks): Format chunks for prompt
   - format_learning_profile(profile): Format profile for prompt
   - build_conversation_messages(history): Format chat history

3. Create specialized prompts for:
   - Opening message when starting a new chapter
   - Handling "I don't understand" responses
   - Wrapping up a session

4. Add prompt for detecting when student needs prerequisites:
   - Analyze student responses for confusion signals
   - Map confusion to specific prerequisite concepts
   - Suggest appropriate chapters

Test the prompts with sample conversations to verify the Socratic approach works well.
```

---

## PHASE 4: Learning Profile System (CRITICAL)

### Prompt 4.1: Conversation Summary Generation

```
Implement the conversation summary system:

1. Create services/summary_service.py:

   class SummaryService:
       async def generate_summary(
           self,
           conversation: Conversation,
           messages: list[Message]
       ) -> ConversationSummary:
           """
           Analyze conversation and generate structured summary.
           """

2. Create the summary generation prompt in prompts/summary_prompt.py:

SUMMARY_PROMPT = '''
Analyze this tutoring conversation and provide a structured assessment.

Conversation about: {chapter_title}
Messages:
{conversation_transcript}

Provide your analysis in the following JSON format:
{
    "summary": "2-3 sentence summary of what was discussed",
    "topics_covered": ["list", "of", "specific", "topics"],
    "concepts_understood": [
        {"concept": "name", "confidence": 0.8, "evidence": "student correctly explained..."}
    ],
    "concepts_struggled": [
        {"concept": "name", "severity": "high|medium|low", "evidence": "student confused about..."}
    ],
    "questions_asked_by_student": 5,
    "engagement_level": "high|medium|low",
    "recommended_next_steps": ["review X", "practice Y"],
    "prerequisite_gaps": ["concepts they seem to be missing"]
}
'''

3. Implement robust JSON parsing:
   - Handle Claude's response formatting variations
   - Validate against Pydantic schema
   - Fallback gracefully if parsing fails

4. Store summary in database with all extracted fields

5. Create tests with sample conversations to verify:
   - Correct identification of understood concepts
   - Correct identification of struggles
   - Appropriate confidence scores
```

### Prompt 4.2: Learning Profile Service

```
Implement the learning profile management:

1. Create services/profile_service.py:

   class ProfileService:
       async def get_or_create_profile(self, user_id: UUID) -> LearningProfile:
           """Get existing profile or create new one."""

       async def update_from_summary(
           self,
           user_id: UUID,
           summary: ConversationSummary,
           chapter: Chapter
       ) -> LearningProfile:
           """
           Update learning profile based on new conversation summary.
           This is called after every conversation ends.
           """

       async def get_recommended_chapters(
           self,
           user_id: UUID,
           book_id: UUID
       ) -> list[ChapterRecommendation]:
           """
           Get personalized chapter recommendations based on profile.
           """

       async def get_context_for_conversation(
           self,
           user_id: UUID,
           chapter_id: UUID
       ) -> ProfileContext:
           """
           Get relevant profile info to include in chat context.
           Includes: related past discussions, known gaps, strengths.
           """

2. Implement the mastery score update algorithm:
   
   def update_mastery_score(
       current_score: float,
       new_evidence: list[ConceptAssessment],
       recency_weight: float = 0.7
   ) -> float:
       """
       Update mastery score using exponential moving average.
       More recent evidence weighted higher.
       Score range: 0.0 (no understanding) to 1.0 (full mastery)
       """

3. Implement gap identification:
   - Track concepts marked as "struggled" across sessions
   - Identify patterns (same concept multiple times = significant gap)
   - Map concepts to chapters that teach them

4. Implement chapter recommendation logic:
   - If current chapter has prerequisites and user hasn't studied them -> recommend prerequisites
   - If user has gaps -> recommend chapters that address those gaps
   - Consider mastery scores when recommending next chapters
   - Factor in logical chapter ordering

5. Create the profile context builder:
   - Pull relevant past conversation summaries for current chapter
   - Include known strengths related to current topic
   - Include known gaps that might affect current topic

6. Add tests for:
   - Mastery score updates correctly
   - Gaps identified after repeated struggles
   - Recommendations make sense
```

### Prompt 4.3: Cross-Conversation Memory

```
Implement cross-conversation memory for continuity:

1. Create services/memory_service.py:

   class MemoryService:
       async def get_relevant_history(
           self,
           user_id: UUID,
           current_chapter_id: UUID,
           current_query: str,
           max_memories: int = 3
       ) -> list[RelevantMemory]:
           """
           Find relevant past interactions to include in current conversation.
           Uses semantic similarity to find related discussions.
           """

       async def format_memories_for_prompt(
           self,
           memories: list[RelevantMemory]
       ) -> str:
           """
           Format memories as natural language for inclusion in prompt.
           Example: "In our previous discussion about Chapter 2, you mentioned 
           struggling with attention mechanisms. Let's connect that to what 
           we're learning now..."
           """

2. Create embeddings for conversation summaries:
   - Add embedding column to conversation_summaries table
   - Generate embedding when summary is created
   - Use same embedding model as RAG

3. Implement semantic search on summaries:
   - Search by similarity to current query
   - Filter by user
   - Optionally filter by related chapters (same book, prerequisite chain)

4. Update the chat service to include relevant memories:
   - Before generating response, fetch relevant memories
   - Include formatted memories in system prompt
   - Reference specific past discussions when relevant

5. Create the memory prompt section:

MEMORY_PROMPT_SECTION = '''
## Relevant Past Discussions
{formatted_memories}

Use these past interactions to:
- Reference concepts you've discussed before
- Acknowledge progress the student has made  
- Connect current topic to previous learning
- Be aware of persistent struggles
'''

6. Test scenarios:
   - User studied Chapter 1, now in Chapter 3 -> reference Chapter 1 concepts
   - User struggled with concept X before -> proactively address it
   - No relevant memories -> gracefully omit section
```

---

## PHASE 5: Frontend Implementation

### Prompt 5.1: Core Layout and Navigation

```
Implement the frontend core structure:

1. Create the main layout in app/layout.tsx:
   - Include AuthProvider
   - Add navigation header
   - Responsive design

2. Create the navigation component:
   - Logo/brand
   - Navigation links (Dashboard, Profile, Logout)
   - Show user name when logged in

3. Create the dashboard page (app/dashboard/page.tsx):
   - Protected route (redirect to login if not authenticated)
   - Header with welcome message
   - Grid of chapter cards
   - Sidebar showing learning profile summary (optional for MVP)

4. Create the API client in lib/api.ts:
   - Axios or fetch wrapper
   - Auto-attach auth token
   - Handle common errors
   - Type-safe request/response

5. Create custom hooks:
   - useChapters(): Fetch and cache chapters
   - useConversations(): Fetch user's conversations
   - useLearningProfile(): Fetch user's profile

Use React Query (TanStack Query) for data fetching and caching.
Ensure all components are properly typed.
```

### Prompt 5.2: Chapter Cards UI

```
Implement the chapter cards interface:

1. Create components/cards/ChapterCard.tsx:
   - Display chapter title, number, summary preview
   - Show mastery indicator (from learning profile):
     - Not started (gray)
     - In progress (yellow)
     - Needs review (orange) - if gaps identified
     - Mastered (green)
   - Show if it's a recommended chapter (highlight/badge)
   - Click to start studying

2. Create components/cards/ChapterGrid.tsx:
   - Responsive grid of chapter cards
   - Group by book (if multiple books later)
   - Sort by chapter number

3. Create components/cards/ChapterDetail.tsx (modal or slide-over):
   - Full chapter info
   - Key concepts list
   - Prerequisites (with links to those chapters)
   - Past conversations for this chapter
   - "Start Studying" button

4. Create the chapters API integration:
   - GET /chapters: List all chapters with user's progress
   - GET /chapters/{id}: Get chapter detail

5. Add loading states and error handling:
   - Skeleton loaders while fetching
   - Error state with retry button

Make the UI clean and modern. Use subtle animations for interactions.
The cards should clearly communicate the user's learning journey at a glance.
```

### Prompt 5.3: Chat Interface

```
Implement the chat interface:

1. Create app/chat/[conversationId]/page.tsx:
   - Full-screen chat view
   - Header with chapter title and back button
   - Message list
   - Input area

2. Create components/chat/MessageList.tsx:
   - Display messages with proper styling (user vs assistant)
   - Auto-scroll to bottom on new messages
   - Support markdown rendering in assistant messages
   - Show typing indicator while streaming

3. Create components/chat/MessageInput.tsx:
   - Text area that grows with content
   - Send button (and Cmd+Enter shortcut)
   - Disabled while waiting for response

4. Create components/chat/StreamingMessage.tsx:
   - Handle SSE streaming from backend
   - Show text as it arrives
   - Smooth animation

5. Create hooks/useChat.ts:
   - Manage conversation state
   - Handle sending messages
   - Handle streaming responses
   - Handle errors

6. Implement the chat flow:
   a. User selects chapter -> POST /conversations -> redirect to chat
   b. Initial assistant message introduces the chapter (Socratic opening)
   c. User sends message -> POST /messages -> stream response
   d. User can end session -> POST /end -> show summary -> redirect to dashboard

7. Create components/chat/SessionSummary.tsx:
   - Modal shown when conversation ends
   - Display summary, topics covered, areas to improve
   - Recommendations for next steps
   - "Return to Dashboard" button

Make the chat feel responsive and polished. 
The streaming should be smooth with no flickering.
```

### Prompt 5.4: Learning Profile Dashboard

```
Implement the learning profile UI:

1. Create app/profile/page.tsx:
   - Overview of learning journey
   - Strengths and gaps visualization
   - Recommended next steps
   - Study history

2. Create components/profile/MasteryOverview.tsx:
   - Visual representation of mastery across chapters
   - Could be: progress bars, heat map, or skill tree
   - Click chapter to see details

3. Create components/profile/GapsSection.tsx:
   - List identified knowledge gaps
   - For each gap show:
     - Concept name
     - Severity (high/medium/low)
     - Related chapter to study
     - "Study Now" button

4. Create components/profile/RecommendationsSection.tsx:
   - Personalized chapter recommendations
   - Explain WHY each is recommended
   - Easy action to start studying

5. Create components/profile/StudyHistory.tsx:
   - Timeline of past study sessions
   - Quick stats: total time, sessions completed
   - Click to view conversation summary

6. Create the profile API integration:
   - GET /profile: Get full learning profile
   - GET /profile/recommendations: Get chapter recommendations

The profile page should motivate the student by showing progress
while also clearly guiding them on what to study next.
```

---

## PHASE 6: Integration & Polish

### Prompt 6.1: End-to-End Integration

```
Integrate all components and ensure the full flow works:

1. Test the complete user journey:
   a. Sign up / Login
   b. View dashboard with chapter cards
   c. See personalized recommendations (even if limited data)
   d. Start conversation on a chapter
   e. Have Socratic dialogue with RAG working
   f. End conversation
   g. See summary generated
   h. Check profile updated with new data
   i. Return to dashboard and see updated mastery indicators
   j. Start new conversation, verify cross-session memory works

2. Fix any integration issues found

3. Add proper error handling throughout:
   - API errors show user-friendly messages
   - Network errors have retry options
   - Auth errors redirect to login

4. Add loading states everywhere:
   - Page-level loading
   - Component-level loading
   - Button loading states

5. Ensure responsive design works:
   - Test on mobile viewport
   - Chat interface usable on phone
   - Cards stack properly on small screens

6. Add proper logging:
   - Backend: Log all API requests, errors, and important events
   - Frontend: Log errors to console (could add error tracking later)

Document any bugs found and fix the critical ones.
```

### Prompt 6.2: Deployment Preparation

```
Prepare the application for deployment:

1. Backend deployment prep:
   - Create production Dockerfile
   - Add health check endpoint (GET /health)
   - Configure for Railway deployment
   - Set up environment variable handling for production
   - Add database connection pooling
   - Configure CORS for production domain

2. Frontend deployment prep:
   - Configure for Vercel deployment
   - Set up environment variables in Vercel
   - Add proper error boundaries
   - Configure production API URL

3. Database setup:
   - Create migration for production (if different from dev)
   - Document Supabase setup steps
   - Ensure pgvector extension is enabled

4. Create deployment documentation:
   - Step-by-step deployment guide
   - Environment variables needed
   - Post-deployment verification steps

5. Add basic monitoring:
   - Backend logging for errors
   - Track API response times
   - (Advanced: set up Sentry for error tracking)

6. Security checklist:
   - No secrets in code
   - CORS properly configured
   - Rate limiting on sensitive endpoints
   - Input validation everywhere

Don't actually deploy yet - just prepare everything.
Create a DEPLOYMENT.md with all the steps.
```

---

## USAGE TIPS FOR CLAUDE CODE

### Before Starting Each Phase
1. Make sure previous phase is complete and tested
2. Review any issues or todos from previous phase
3. Read the CLAUDE.md file to ensure context is fresh

### During Implementation
- If Claude proposes a different approach, ask it to explain why
- Use `/review` command after significant changes
- Run tests frequently: `!pytest tests/ -v`
- Commit after each working feature: `!git add -A && git commit -m "feat: description"`

### If Something Breaks
```
The [X feature] is broken. Here's the error:
[paste error]

Debug this issue:
1. Identify the root cause
2. Explain what went wrong
3. Fix it
4. Add a test to prevent regression
```

### To Get Explanations
```
Explain why you implemented [X] this way. 
I want to understand the design decision so I can make similar choices in the future.
```

### To Iterate on Quality
```
/review the chat service implementation

Focus especially on:
- Error handling completeness
- Edge cases
- Code cleanliness
```

---

## QUICK REFERENCE: Slash Commands

Once you have the .claude/commands/ set up:

- `/project:implement-feature [description]` - Implement a new feature
- `/project:review [files or scope]` - Code review
- `/project:add-tests [component]` - Add tests

---

## ESTIMATED TIMELINE

| Phase | Effort | Description |
|-------|--------|-------------|
| Phase 0 | 1-2 hours | Project setup |
| Phase 1 | 2-3 hours | Authentication |
| Phase 2 | 3-4 hours | Book ingestion & RAG |
| Phase 3 | 4-5 hours | Chat & Socratic dialogue |
| Phase 4 | 4-5 hours | Learning profile system |
| Phase 5 | 5-6 hours | Frontend implementation |
| Phase 6 | 2-3 hours | Integration & polish |

**Total: ~20-30 hours** (spread across multiple sessions)

Start with Phase 0 and 1, then upload your book PDF before Phase 2.
