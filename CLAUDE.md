# AI Socratic Tutor - Project Context

## Project Overview
An AI-powered Socratic teaching assistant that helps students learn AI concepts through guided dialogue. Users select chapter cards, engage in Socratic conversations with an AI tutor that uses RAG to reference book content, and build a learning profile that tracks their progress and gaps.

## Tech Stack
- **Frontend**: Next.js 14 with TypeScript, Tailwind CSS
- **Backend**: FastAPI (Python 3.12)
- **Database**: PostgreSQL with pgvector extension
- **Authentication**: Supabase Auth
- **LLM**: Claude API (claude-sonnet-4-20250514)
- **Embedding Model**: OpenAI text-embedding-3-small (or Voyage AI)
- **Hosting**: Vercel (frontend), Railway (backend), Supabase (database)

## Architecture Principles
- Clean, modular code with clear separation of concerns
- Type hints on ALL Python functions, TypeScript strict mode
- Repository pattern for database access
- Service layer for business logic
- Dependency injection for testability
- Comprehensive error handling with custom exceptions
- API versioning (/api/v1/...)
- Environment-based configuration

## Project Structure
```
socratic-tutor/
├── frontend/                 # Next.js app
│   ├── src/
│   │   ├── app/             # App router pages
│   │   ├── components/      # React components
│   │   │   ├── ui/          # Reusable UI components
│   │   │   ├── chat/        # Chat-related components
│   │   │   └── cards/       # Chapter card components
│   │   ├── lib/             # Utilities, API client
│   │   ├── hooks/           # Custom React hooks
│   │   ├── types/           # TypeScript types
│   │   └── styles/          # Global styles
│   └── public/
├── backend/                  # FastAPI app
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       └── router.py
│   │   ├── core/            # Config, security, dependencies
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   │   ├── rag_service.py
│   │   │   ├── chat_service.py
│   │   │   ├── profile_service.py
│   │   │   └── embedding_service.py
│   │   ├── repositories/    # Database access layer
│   │   └── utils/
│   ├── scripts/             # Data ingestion, migrations
│   ├── tests/
│   └── alembic/             # Database migrations
├── docs/                     # Documentation
├── scripts/                  # Utility scripts
└── docker-compose.yml
```

## Database Schema (Core Tables)

### users
- id (UUID, PK)
- supabase_id (VARCHAR, unique) - links to Supabase Auth
- email (VARCHAR)
- name (VARCHAR)
- created_at (TIMESTAMP)

### books
- id (UUID, PK)
- title (VARCHAR)
- author (VARCHAR)
- description (TEXT)
- created_at (TIMESTAMP)

### chapters
- id (UUID, PK)
- book_id (UUID, FK)
- title (VARCHAR)
- chapter_number (INT)
- summary (TEXT)
- prerequisites (UUID[]) - chapters that should be studied first
- key_concepts (VARCHAR[])
- created_at (TIMESTAMP)

### chunks
- id (UUID, PK)
- chapter_id (UUID, FK)
- content (TEXT)
- embedding (VECTOR(1536))
- chunk_index (INT)
- section_title (VARCHAR, nullable)
- metadata (JSONB) - page numbers, headings, etc.

### conversations
- id (UUID, PK)
- user_id (UUID, FK)
- chapter_id (UUID, FK)
- started_at (TIMESTAMP)
- ended_at (TIMESTAMP, nullable)
- status (ENUM: active, completed, abandoned)

### messages
- id (UUID, PK)
- conversation_id (UUID, FK)
- role (ENUM: user, assistant, system)
- content (TEXT)
- created_at (TIMESTAMP)

### conversation_summaries
- id (UUID, PK)
- conversation_id (UUID, FK, unique)
- summary (TEXT)
- topics_covered (VARCHAR[])
- concepts_understood (VARCHAR[])
- concepts_struggled (VARCHAR[])
- questions_asked (INT)
- engagement_score (FLOAT)
- created_at (TIMESTAMP)

### learning_profiles
- id (UUID, PK)
- user_id (UUID, FK, unique)
- mastery_map (JSONB) - {"chapter_id": {"score": 0.8, "last_studied": "..."}}
- identified_gaps (JSONB[]) - [{"concept": "...", "severity": "high", "related_chapters": [...]}]
- strengths (VARCHAR[])
- recommended_chapters (UUID[])
- total_study_time_minutes (INT)
- updated_at (TIMESTAMP)

## Key Features (MVP Priority)

### P0 - Must Have for MVP
1. User authentication (Supabase)
2. Chapter cards display with book info
3. Socratic chat interface with RAG
4. Real-time learning profile updates after each session
5. Basic chapter recommendations based on profile

### P1 - Important but can be basic
1. Conversation history view
2. Profile dashboard showing strengths/gaps
3. Cross-conversation context ("remember when we discussed...")

### P2 - Nice to have
1. Progress visualization
2. Paper recommendations
3. Quiz generation

## Coding Standards

### Python (Backend)
- Use Black formatter (line length 88)
- Use Ruff for linting
- Type hints required on all functions
- Docstrings for all public functions (Google style)
- Async functions for I/O operations
- Use Pydantic for all data validation
- Environment variables via pydantic-settings

### TypeScript (Frontend)
- Strict mode enabled
- ESLint + Prettier
- Functional components only
- Custom hooks for shared logic
- Zod for runtime validation
- Server components by default, client only when needed

### API Design
- RESTful endpoints
- Consistent error response format: {"detail": "...", "code": "ERROR_CODE"}
- Pagination for list endpoints
- Request/response schemas documented

### Git
- Conventional commits (feat:, fix:, docs:, refactor:)
- Feature branches
- No direct commits to main

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...
SUPABASE_SERVICE_KEY=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...  # for embeddings
CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend (.env.local)
```
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Critical Implementation Notes

### RAG Implementation
- Chunk size: 500-800 tokens with 100 token overlap
- Store section metadata with each chunk
- Use hybrid search: semantic (pgvector) + keyword (full-text)
- Rerank results before sending to LLM
- Include chapter context in retrieval

### Learning Profile Updates
After each conversation ends:
1. Generate conversation summary via LLM
2. Extract concepts understood vs struggled
3. Update mastery_map scores (weighted average with recency)
4. Identify new gaps
5. Recalculate chapter recommendations

### Socratic Prompt Strategy
The AI should:
- Never give direct answers immediately
- Ask probing questions to assess understanding
- Build on student's existing knowledge
- Provide hints before explanations
- Use analogies and examples
- Check understanding before moving on

## Testing Requirements
- Unit tests for services (pytest)
- Integration tests for API endpoints
- E2E tests for critical flows (Playwright)
- Minimum 70% coverage for services

## Performance Targets
- Chat response: < 3s for first token
- Chapter list load: < 500ms
- Support 100 concurrent users initially
