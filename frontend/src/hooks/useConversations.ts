/**
 * Custom hook for fetching and managing conversations
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";

// Query keys for cache management
export const conversationKeys = {
  all: ["conversations"] as const,
  lists: () => [...conversationKeys.all, "list"] as const,
  list: (filters?: { limit?: number; offset?: number }) =>
    [...conversationKeys.lists(), filters] as const,
  details: () => [...conversationKeys.all, "detail"] as const,
  detail: (id: string) => [...conversationKeys.details(), id] as const,
};

/**
 * Fetch user's conversations
 */
export function useConversations(limit = 20, offset = 0) {
  return useQuery({
    queryKey: conversationKeys.list({ limit, offset }),
    queryFn: () => apiClient.getConversations(limit, offset),
    staleTime: 1 * 60 * 1000, // Conversations are more dynamic
  });
}

/**
 * Fetch a single conversation with messages
 */
export function useConversation(conversationId: string) {
  return useQuery({
    queryKey: conversationKeys.detail(conversationId),
    queryFn: () => apiClient.getConversation(conversationId),
    enabled: !!conversationId,
    staleTime: 30 * 1000, // 30 seconds - conversations are active
  });
}

/**
 * Create a new conversation
 */
export function useCreateConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (chapterId: string) => apiClient.createConversation(chapterId),
    onSuccess: () => {
      // Invalidate conversations list to include the new one
      queryClient.invalidateQueries({ queryKey: conversationKeys.lists() });
    },
  });
}

/**
 * End a conversation
 */
export function useEndConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (conversationId: string) =>
      apiClient.endConversation(conversationId),
    onSuccess: (_, conversationId) => {
      // Invalidate both the specific conversation and the list
      queryClient.invalidateQueries({
        queryKey: conversationKeys.detail(conversationId),
      });
      queryClient.invalidateQueries({ queryKey: conversationKeys.lists() });
    },
  });
}

/**
 * Get recent conversations for a specific chapter
 */
export function useChapterConversations(chapterId: string) {
  const { data: conversations, ...rest } = useConversations();

  const chapterConversations = conversations?.filter(
    (conv) => conv.chapter_id === chapterId
  );

  return {
    ...rest,
    data: chapterConversations,
    conversations: chapterConversations,
  };
}

/**
 * Get active conversation if any
 */
export function useActiveConversation() {
  const { data: conversations, ...rest } = useConversations();

  const activeConversation = conversations?.find(
    (conv) => conv.status === "active"
  );

  return {
    ...rest,
    data: activeConversation,
    activeConversation,
  };
}
