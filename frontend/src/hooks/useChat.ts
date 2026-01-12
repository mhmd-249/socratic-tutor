/**
 * Custom hook for managing chat/conversation state
 * Handles message sending, streaming responses, and conversation lifecycle
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { apiClient } from "@/lib/api";
import type { Message, ConversationSummary, ChapterWithBook } from "@/types";

interface ChatState {
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
  streamingContent: string;
  error: string | null;
  conversationId: string | null;
  chapter: ChapterWithBook | null;
  summary: ConversationSummary | null;
  isEnding: boolean;
}

interface UseChatReturn extends ChatState {
  sendMessage: (content: string) => Promise<void>;
  endConversation: () => Promise<void>;
  startConversation: (chapterId: string) => Promise<string | null>;
  loadConversation: (conversationId: string) => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

const initialState: ChatState = {
  messages: [],
  isLoading: false,
  isStreaming: false,
  streamingContent: "",
  error: null,
  conversationId: null,
  chapter: null,
  summary: null,
  isEnding: false,
};

export function useChat(): UseChatReturn {
  const [state, setState] = useState<ChatState>(initialState);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  /**
   * Start a new conversation for a chapter
   */
  const startConversation = useCallback(async (chapterId: string): Promise<string | null> => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      // Create conversation
      const response = await apiClient.createConversation(chapterId);

      // Fetch chapter details
      const chapter = await apiClient.getChapter(chapterId);

      // Create initial assistant message
      const initialMessage: Message = {
        id: `initial-${Date.now()}`,
        conversation_id: response.id,
        role: "assistant",
        content: response.initial_message,
        created_at: new Date().toISOString(),
      };

      setState((prev) => ({
        ...prev,
        conversationId: response.id,
        chapter,
        messages: [initialMessage],
        isLoading: false,
      }));

      return response.id;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to start conversation";
      setState((prev) => ({ ...prev, error: message, isLoading: false }));
      return null;
    }
  }, []);

  /**
   * Load an existing conversation
   */
  const loadConversation = useCallback(async (conversationId: string): Promise<void> => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      // Fetch conversation with messages
      const data = await apiClient.getConversation(conversationId);

      // Fetch chapter details
      const chapter = await apiClient.getChapter(data.conversation.chapter_id);

      setState((prev) => ({
        ...prev,
        conversationId,
        chapter,
        messages: data.messages,
        isLoading: false,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load conversation";
      setState((prev) => ({ ...prev, error: message, isLoading: false }));
    }
  }, []);

  /**
   * Send a message and handle streaming response
   */
  const sendMessage = useCallback(async (content: string): Promise<void> => {
    if (!state.conversationId || state.isStreaming) return;

    // Add user message immediately
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      conversation_id: state.conversationId,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };

    setState((prev) => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isStreaming: true,
      streamingContent: "",
      error: null,
    }));

    try {
      // Cancel any existing request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      // Send message and get streaming response
      const response = await apiClient.sendMessage(state.conversationId, content);

      if (!response.body) {
        throw new Error("No response body");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.error) {
                throw new Error(data.error);
              }

              if (data.done) {
                // Streaming complete - add final message
                const assistantMessage: Message = {
                  id: `assistant-${Date.now()}`,
                  conversation_id: state.conversationId!,
                  role: "assistant",
                  content: fullContent,
                  created_at: new Date().toISOString(),
                };

                setState((prev) => ({
                  ...prev,
                  messages: [...prev.messages, assistantMessage],
                  isStreaming: false,
                  streamingContent: "",
                }));
                return;
              }

              if (data.content) {
                fullContent += data.content;
                setState((prev) => ({
                  ...prev,
                  streamingContent: fullContent,
                }));
              }
            } catch {
              // Skip invalid JSON lines
              if (line.trim() && !line.startsWith("data: ")) {
                console.warn("Failed to parse SSE line:", line);
              }
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        return; // Request was cancelled, don't show error
      }

      const message = error instanceof Error ? error.message : "Failed to send message";
      setState((prev) => ({
        ...prev,
        error: message,
        isStreaming: false,
        streamingContent: "",
      }));
    }
  }, [state.conversationId, state.isStreaming]);

  /**
   * End the conversation and get summary
   */
  const endConversation = useCallback(async (): Promise<void> => {
    if (!state.conversationId) return;

    setState((prev) => ({ ...prev, isEnding: true, error: null }));

    try {
      const summary = await apiClient.endConversation(state.conversationId);
      setState((prev) => ({ ...prev, summary, isEnding: false }));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to end conversation";
      setState((prev) => ({ ...prev, error: message, isEnding: false }));
    }
  }, [state.conversationId]);

  /**
   * Clear error state
   */
  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  /**
   * Reset chat state
   */
  const reset = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setState(initialState);
  }, []);

  return {
    ...state,
    sendMessage,
    endConversation,
    startConversation,
    loadConversation,
    clearError,
    reset,
  };
}
