# Socratic Tutor AI Engine - Integration Requirements

This document outlines the requirements for integrating the Socratic Tutor AI engine into an external software system. The AI engine handles Socratic-style tutoring conversations, RAG-based content retrieval, learning profile management, and cross-conversation memory.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [External API Dependencies](#2-external-api-dependencies)
3. [Database Requirements](#3-database-requirements)
4. [Data Models & Schemas](#4-data-models--schemas)
5. [Core Services](#5-core-services)
6. [Input/Output Specifications](#6-inputoutput-specifications)
7. [Configuration Requirements](#7-configuration-requirements)
8. [Integration Points](#8-integration-points)
9. [Minimum Viable Integration](#9-minimum-viable-integration)
10. [Full Integration](#10-full-integration)

---

## 1. Architecture Overview

The AI engine consists of six interconnected services:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SOCRATIC TUTOR AI ENGINE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │ Chat Service │───▶│ RAG Service  │───▶│ Embedding Service        │  │
│  │ (Orchestrator)│   │ (Retrieval)  │    │ (OpenAI text-embedding)  │  │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘  │
│         │                   │                                           │
│         ▼                   ▼                                           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │Memory Service│    │Profile Svc   │    │ Summary Service          │  │
│  │(Cross-convo) │    │(Learning     │◀───│ (Conversation Analysis)  │  │
│  │              │    │ Tracking)    │    │                          │  │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │      External APIs            │
                    ├───────────────────────────────┤
                    │ • Claude API (Anthropic)      │
                    │ • OpenAI Embeddings API       │
                    │ • PostgreSQL + pgvector       │
                    └───────────────────────────────┘
```

---

## 2. External API Dependencies

### 2.1 Claude API (Anthropic) - REQUIRED

**Purpose**: Powers all LLM interactions (tutoring responses, conversation analysis)

| Attribute | Value |
|-----------|-------|
| Model | `claude-sonnet-4-20250514` (Claude 3.5 Sonnet) |
| Max Output Tokens | 2,000 per response |
| Streaming | Required for real-time responses |
| API Version | Latest Anthropic SDK (async) |

**API Key**: `ANTHROPIC_API_KEY`

**Usage Patterns**:
- Streaming chat completions for tutoring
- Non-streaming for conversation summary analysis

**Estimated Costs** (per conversation):
- Input: ~4,000-8,000 tokens (context + RAG)
- Output: ~500-2,000 tokens per response
- Summary: ~2,000-4,000 tokens per conversation end

### 2.2 OpenAI Embeddings API - REQUIRED

**Purpose**: Generate vector embeddings for semantic search

| Attribute | Value |
|-----------|-------|
| Model | `text-embedding-3-small` |
| Dimensions | 1,536 |
| Batch Size | Up to 100 texts per API call |

**API Key**: `OPENAI_API_KEY`

**Usage Patterns**:
- Content ingestion: Embed all course content chunks
- Query embedding: Each user message requires embedding
- Summary embedding: Store for cross-conversation search

**Alternative**: Can be replaced with any embedding model producing 1,536-dimensional vectors (e.g., Voyage AI, Cohere)

---

## 3. Database Requirements

### 3.1 PostgreSQL with pgvector Extension - REQUIRED

**Minimum Version**: PostgreSQL 14+ with pgvector 0.5.0+

**Required Extensions**:
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
```

### 3.2 Required Tables

| Table | Purpose | Critical Fields |
|-------|---------|-----------------|
| `chunks` | Store content with embeddings | `embedding VECTOR(1536)`, `content TEXT`, `content_tsv TSVECTOR` |
| `conversation_summaries` | Store analyzed conversations | `embedding VECTOR(1536)`, `concepts_understood`, `concepts_struggled` |
| `learning_profiles` | Track student progress | `mastery_map JSONB`, `identified_gaps JSONB`, `strengths ARRAY` |
| `conversations` | Track chat sessions | `user_id`, `chapter_id`, `status`, `started_at`, `ended_at` |
| `messages` | Store conversation messages | `role ENUM`, `content TEXT`, `conversation_id` |

### 3.3 Required Indexes

```sql
-- Vector similarity search
CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON conversation_summaries USING ivfflat (embedding vector_cosine_ops);

-- Full-text search
CREATE INDEX ON chunks USING GIN (content_tsv);

-- Standard indexes
CREATE INDEX ON messages (conversation_id, created_at);
CREATE INDEX ON conversations (user_id, started_at);
CREATE INDEX ON learning_profiles (user_id);
```

---

## 4. Data Models & Schemas

### 4.1 Content Chunk (for RAG)

```typescript
interface Chunk {
  id: UUID;
  chapter_id: UUID;                    // Link to your content structure
  content: string;                      // Text content (500-800 tokens recommended)
  embedding: number[];                  // 1536-dimensional vector
  chunk_index: number;                  // Position in chapter
  section_title?: string;               // Optional section header
  chunk_metadata?: {                    // Optional metadata
    page_numbers?: number[];
    headings?: string[];
  };
}
```

### 4.2 Learning Profile

```typescript
interface LearningProfile {
  id: UUID;
  user_id: UUID;
  mastery_map: {
    [chapter_id: string]: {
      score: number;                    // 0.0 - 1.0
      last_studied: string;             // ISO datetime
      study_count: number;
      concepts_covered: string[];
    };
  };
  identified_gaps: Array<{
    concept: string;
    severity: "high" | "medium" | "low";
    occurrence_count: number;
    related_chapters: UUID[];
    first_seen: string;
    last_seen: string;
  }>;
  strengths: string[];                  // Demonstrated strong concepts
  recommended_chapters: UUID[];
  total_study_time_minutes: number;
  updated_at: string;
}
```

### 4.3 Conversation Summary

```typescript
interface ConversationSummary {
  id: UUID;
  conversation_id: UUID;
  summary: string;                      // 2-3 sentence narrative
  topics_covered: string[];
  concepts_understood: string[];
  concepts_struggled: string[];
  questions_asked: number;              // Count of student questions
  engagement_score: number;             // 0.0 - 1.0
  embedding?: number[];                 // For cross-conversation search
  created_at: string;
}
```

### 4.4 Message

```typescript
interface Message {
  id: UUID;
  conversation_id: UUID;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}
```

### 4.5 Content Context (Your System Must Provide)

```typescript
interface ChapterContext {
  chapter_id: UUID;
  chapter_title: string;
  chapter_number: number;
  book_title: string;
  book_author?: string;
  summary?: string;                     // Chapter overview
  key_concepts?: string[];              // Main topics covered
  prerequisites?: UUID[];               // Previous chapters required
}
```

---

## 5. Core Services

### 5.1 Chat Service (Orchestrator)

**Purpose**: Manages conversation flow and coordinates other services

**Key Methods**:

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `create_conversation` | `user_id`, `chapter_id` | `Conversation` + initial greeting | Starts new tutoring session |
| `send_message` | `conversation_id`, `message` | `AsyncGenerator[str]` | Streams AI response |
| `end_conversation` | `conversation_id` | `ConversationSummary` | Closes session, triggers analysis |

**Dependencies**: RAG Service, Memory Service, Profile Service, Summary Service

### 5.2 RAG Service

**Purpose**: Retrieves relevant content using hybrid search

**Key Methods**:

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `retrieve` | `query`, `chapter_id`, `top_k` | `RetrievedChunk[]` | Hybrid semantic + keyword search |
| `format_context_for_llm` | `chunks`, `max_tokens` | `string` | Formats for prompt |

**Search Algorithm**:
```
combined_score = (0.7 × semantic_similarity) + (0.3 × keyword_score)
```

### 5.3 Embedding Service

**Purpose**: Generate vector embeddings

**Key Methods**:

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `generate_embedding` | `text` | `number[]` | Single text embedding |
| `generate_embeddings` | `texts[]` | `number[][]` | Batch embeddings |

### 5.4 Memory Service

**Purpose**: Cross-conversation continuity

**Key Methods**:

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `get_relevant_history` | `user_id`, `chapter_id`, `query` | `RelevantMemory[]` | Finds related past discussions |
| `format_memories_for_prompt` | `memories` | `string` | Formats for context |

**Memory Ranking**:
- Same book: +0.1 boost
- Prerequisite chapter: +0.2 boost
- Contains struggled concepts: +0.1 boost

### 5.5 Profile Service

**Purpose**: Tracks learning progress and generates recommendations

**Key Methods**:

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `get_or_create_profile` | `user_id` | `LearningProfile` | Gets/creates profile |
| `update_from_summary` | `user_id`, `summary`, `chapter` | `LearningProfile` | Updates after conversation |
| `get_recommended_chapters` | `user_id` | `ChapterRecommendation[]` | Generates suggestions |

**Mastery Score Algorithm**:
```
new_score = (0.7 × evidence_score) + (0.3 × previous_score)
```

### 5.6 Summary Service

**Purpose**: Analyzes conversations for learning insights

**Key Methods**:

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `generate_summary` | `conversation`, `messages` | `ConversationSummary` | Full analysis via Claude |

**Output Structure** (JSON from Claude):
```json
{
  "summary": "Brief narrative",
  "topics_covered": ["topic1", "topic2"],
  "concepts_understood": [
    {"concept": "X", "confidence": 0.8, "evidence": "..."}
  ],
  "concepts_struggled": [
    {"concept": "Y", "severity": "high", "evidence": "..."}
  ],
  "engagement_score": 0.75
}
```

---

## 6. Input/Output Specifications

### 6.1 Starting a Conversation

**Input Required**:
```typescript
{
  user_id: UUID,           // Your user identifier
  chapter_id: UUID,        // Content chapter to study
}
```

**Your System Must Provide**:
- Chapter context (title, summary, key concepts)
- Pre-embedded content chunks for the chapter
- User's learning profile (or empty profile for new users)

**Output**:
```typescript
{
  conversation_id: UUID,
  initial_message: string,  // Personalized Socratic greeting
}
```

### 6.2 Sending a Message

**Input**:
```typescript
{
  conversation_id: UUID,
  message: string,         // User's message
}
```

**Processing Flow**:
1. Save user message to database
2. Generate query embedding
3. Retrieve relevant chunks (RAG)
4. Get learning profile context
5. Get cross-conversation memories
6. Build system prompt with all context
7. Stream response from Claude

**Output**: `AsyncGenerator<string>` (streaming text chunks)

### 6.3 Ending a Conversation

**Input**:
```typescript
{
  conversation_id: UUID,
}
```

**Processing Flow**:
1. Mark conversation as completed
2. Generate summary via Claude (JSON analysis)
3. Update learning profile:
   - Mastery scores (exponential moving average)
   - Identified gaps (fuzzy matching for deduplication)
   - Strengths (high-confidence understood concepts)
   - Recommendations (priority-based)
4. Generate summary embedding for memory search

**Output**:
```typescript
{
  summary: ConversationSummary,
  updated_profile: LearningProfile,
}
```

---

## 7. Configuration Requirements

### 7.1 Required Environment Variables

```env
# API Keys (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-...       # Claude API access
OPENAI_API_KEY=sk-...              # Embeddings API access

# Database (REQUIRED)
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

### 7.2 Configurable Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MAX_CONTEXT_MESSAGES` | 20 | Messages to include in conversation history |
| `RAG_TOKEN_BUDGET` | 4000 | Max tokens for RAG context |
| `RAG_TOP_K` | 5 | Number of chunks to retrieve |
| `RAG_SEMANTIC_WEIGHT` | 0.7 | Weight for semantic search |
| `RAG_KEYWORD_WEIGHT` | 0.3 | Weight for keyword search |
| `RAG_SIMILARITY_THRESHOLD` | 0.7 | Minimum similarity score |
| `MASTERY_RECENCY_WEIGHT` | 0.7 | Weight for new evidence vs old score |
| `MAX_MEMORIES` | 3 | Cross-conversation memories to include |
| `CHUNK_TARGET_SIZE` | 600 | Target tokens per chunk |
| `CHUNK_MAX_SIZE` | 800 | Maximum tokens per chunk |
| `CHUNK_OVERLAP` | 100 | Overlap tokens between chunks |

---

## 8. Integration Points

### 8.1 Content Ingestion (One-Time Setup)

Your system must prepare content before tutoring can begin:

```
Your Content → Chunking Service → Embedding Service → Database
```

**Steps**:
1. Split content into chunks (500-800 tokens each, 100 token overlap)
2. Generate embeddings for each chunk
3. Store chunks with embeddings in `chunks` table
4. Create full-text search index (`tsvector`)

### 8.2 User Management Hook

When a new user is created in your system:
```typescript
// Create empty learning profile
await profileService.get_or_create_profile(user_id);
```

### 8.3 Conversation Lifecycle Hooks

```typescript
// Your system calls these at appropriate times:

// 1. User selects a chapter to study
const { conversation_id, initial_message } = await chatService.create_conversation(
  user_id,
  chapter_id
);

// 2. User sends a message (streaming)
for await (const chunk of chatService.send_message(conversation_id, message)) {
  // Stream to your UI
  yield chunk;
}

// 3. User ends session
const summary = await chatService.end_conversation(conversation_id);
// Show summary to user, redirect to dashboard, etc.
```

### 8.4 Profile Data Access

For displaying progress in your UI:
```typescript
const profile = await profileService.get_or_create_profile(user_id);
const recommendations = await profileService.get_recommended_chapters(user_id);
```

---

## 9. Minimum Viable Integration

For a basic integration with core tutoring functionality:

### Required Components

| Component | Required | Notes |
|-----------|----------|-------|
| Chat Service | Yes | Core orchestrator |
| RAG Service | Yes | Content retrieval |
| Embedding Service | Yes | Semantic search |
| Summary Service | Yes | Conversation analysis |
| Profile Service | Optional | Can skip learning tracking initially |
| Memory Service | Optional | Can skip cross-conversation memory |

### Minimum Data Requirements

1. **Content Chunks** with embeddings
2. **Chapter Context** (title, summary, key concepts)
3. **Message Storage** (conversation history)

### Minimum API Keys

- `ANTHROPIC_API_KEY` (Claude)
- `OPENAI_API_KEY` (Embeddings)

### Simplified Flow

```
User Message
    ↓
Generate Embedding
    ↓
Retrieve Relevant Chunks (RAG)
    ↓
Build Socratic Prompt
    ↓
Stream Claude Response
    ↓
Save Messages
```

---

## 10. Full Integration

For complete functionality with learning tracking and personalization:

### All Components Required

All six services fully integrated with:
- Learning profile persistence
- Cross-conversation memory
- Personalized recommendations
- Gap tracking and remediation

### Additional Data Requirements

1. **Learning Profiles** with mastery tracking
2. **Conversation Summaries** with embeddings
3. **Prerequisite relationships** between chapters

### Enhanced Features

- Personalized greetings referencing known struggles
- Cross-conversation context ("Last time we discussed...")
- Adaptive recommendations based on gaps
- Progress tracking and visualization data

---

## Appendix A: Socratic Prompting Principles

The AI engine follows these 8 core teaching principles:

1. **Never give direct answers immediately** - Guide through questioning
2. **Ask probing questions** - Assess understanding before explaining
3. **Build on existing knowledge** - Create bridges to new concepts
4. **Provide hints, not solutions** - Progressive disclosure
5. **Use analogies and examples** - Real-world connections
6. **Check understanding frequently** - Verification questions
7. **Be encouraging and patient** - Normalize confusion
8. **Stay focused on chapter concepts** - Avoid tangents

---

## Appendix B: Sample System Prompt Structure

```
[SOCRATIC_SYSTEM_PROMPT - Teaching methodology]

## CHAPTER CONTEXT
Book: {book_title}
Chapter {chapter_number}: {chapter_title}
Summary: {chapter_summary}
Key Concepts: {key_concepts}

## RELEVANT TEXTBOOK CONTENT
{formatted_rag_chunks}

## STUDENT'S LEARNING PROFILE
Strengths: {strengths}
Known Struggles: {identified_gaps with severity}

## PREVIOUS RELATED DISCUSSIONS
{formatted_memories}
```

---

## Appendix C: Technology Stack Summary

| Layer | Technology | Version |
|-------|------------|---------|
| LLM | Claude (Anthropic) | claude-sonnet-4-20250514 |
| Embeddings | OpenAI | text-embedding-3-small |
| Vector DB | PostgreSQL + pgvector | 14+ / 0.5.0+ |
| Tokenizer | tiktoken | cl100k_base |
| Async Runtime | Python asyncio | 3.12+ |

---

## Appendix D: Error Handling

The AI engine includes graceful degradation:

| Scenario | Fallback Behavior |
|----------|-------------------|
| Embedding generation fails | Uses recent conversations instead of semantic search |
| Claude analysis fails | Returns basic summary from message statistics |
| Memory search fails | Proceeds without cross-conversation context |
| Profile doesn't exist | Creates new empty profile |

---

## Document Version

- **Version**: 1.0
- **Last Updated**: January 2025
- **Repository**: Socratic Tutor
