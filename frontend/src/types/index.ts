/**
 * TypeScript types for API responses and domain models
 */

import { z } from "zod";

// ============================================================================
// User Types
// ============================================================================

export interface User {
  id: string;
  supabase_id: string;
  email: string;
  name: string;
  created_at: string;
}

// ============================================================================
// Book Types
// ============================================================================

export interface Book {
  id: string;
  title: string;
  author: string;
  description: string | null;
  created_at: string;
}

// ============================================================================
// Chapter Types
// ============================================================================

export interface Chapter {
  id: string;
  book_id: string;
  title: string;
  chapter_number: number;
  summary: string | null;
  prerequisites: string[] | null;
  key_concepts: string[] | null;
  created_at: string;
}

export interface ChapterWithBook extends Chapter {
  book: Book;
}

// Zod schema for runtime validation
export const ChapterSchema = z.object({
  id: z.string().uuid(),
  book_id: z.string().uuid(),
  title: z.string(),
  chapter_number: z.number(),
  summary: z.string().nullable(),
  prerequisites: z.array(z.string()).nullable(),
  key_concepts: z.array(z.string()).nullable(),
  created_at: z.string(),
});

// ============================================================================
// Conversation Types
// ============================================================================

export type ConversationStatus = "active" | "completed" | "abandoned";

export interface Conversation {
  id: string;
  user_id: string;
  chapter_id: string;
  started_at: string;
  ended_at: string | null;
  status: ConversationStatus;
}

export interface ConversationWithDetails extends Conversation {
  chapter_title?: string;
  book_title?: string;
  message_count?: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export interface ConversationWithMessages {
  conversation: Conversation;
  messages: Message[];
}

// ============================================================================
// Conversation Summary Types
// ============================================================================

export interface ConversationSummary {
  id: string;
  conversation_id: string;
  summary: string;
  topics_covered: string[];
  concepts_understood: string[];
  concepts_struggled: string[];
  questions_asked: number;
  engagement_score: number;
  created_at: string;
}

// ============================================================================
// Learning Profile Types
// ============================================================================

export interface IdentifiedGap {
  concept: string;
  severity: "high" | "medium" | "low";
  related_chapters: string[];
  occurrence_count: number;
  last_seen: string;
}

export interface MasteryEntry {
  score: number;
  last_studied: string;
  study_count: number;
}

export interface LearningProfile {
  id: string;
  user_id: string;
  mastery_map: Record<string, MasteryEntry>;
  identified_gaps: IdentifiedGap[];
  strengths: string[];
  recommended_chapters: string[];
  total_study_time_minutes: number;
  updated_at: string;
}

// ============================================================================
// API Response Types
// ============================================================================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  code?: string;
}

// ============================================================================
// Chat Types
// ============================================================================

export interface CreateConversationRequest {
  chapter_id: string;
}

export interface SendMessageRequest {
  message: string;
}

export interface CreateConversationResponse {
  id: string;
  user_id: string;
  chapter_id: string;
  started_at: string;
  status: ConversationStatus;
  initial_message: string;
}
