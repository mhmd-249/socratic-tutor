/**
 * Custom hook for fetching and caching chapters
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { ChapterWithBook } from "@/types";

// Query keys for cache management
export const chapterKeys = {
  all: ["chapters"] as const,
  lists: () => [...chapterKeys.all, "list"] as const,
  list: (bookId?: string) => [...chapterKeys.lists(), { bookId }] as const,
  details: () => [...chapterKeys.all, "detail"] as const,
  detail: (id: string) => [...chapterKeys.details(), id] as const,
};

/**
 * Fetch all chapters, optionally filtered by book
 */
export function useChapters(bookId?: string) {
  return useQuery({
    queryKey: chapterKeys.list(bookId),
    queryFn: () => apiClient.getChapters(bookId),
    staleTime: 10 * 60 * 1000, // Chapters don't change often
  });
}

/**
 * Fetch a single chapter by ID
 */
export function useChapter(chapterId: string) {
  return useQuery({
    queryKey: chapterKeys.detail(chapterId),
    queryFn: () => apiClient.getChapter(chapterId),
    enabled: !!chapterId,
  });
}

/**
 * Group chapters by book for display
 */
export function useChaptersGroupedByBook() {
  const query = useChapters();

  const groupedChapters = query.data?.reduce(
    (acc, chapter) => {
      const bookId = chapter.book_id;
      if (!acc[bookId]) {
        acc[bookId] = {
          book: chapter.book,
          chapters: [],
        };
      }
      acc[bookId].chapters.push(chapter);
      return acc;
    },
    {} as Record<string, { book: ChapterWithBook["book"]; chapters: ChapterWithBook[] }>
  );

  // Sort chapters within each book by chapter number
  if (groupedChapters) {
    Object.values(groupedChapters).forEach((group) => {
      group.chapters.sort((a, b) => a.chapter_number - b.chapter_number);
    });
  }

  return {
    ...query,
    groupedChapters,
  };
}
